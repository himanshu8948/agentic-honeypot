from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass
from typing import Iterable


_RE_WS = re.compile(r"\s+")
_RE_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_RE_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_RE_PHONE = re.compile(r"\+?\d[\d\-\s]{7,}\d")

# Avoid lines that accidentally mention security-sensitive tokens that can derail the honeypot
# or look like "we are training scams". This is strictly for neutral "story bridge" filler.
_SENSITIVE_TOKENS = {
    "otp",
    "upi",
    "pin",
    "password",
    "cvv",
    "anydesk",
    "teamviewer",
    "remote",
    "bank",
    "account",
    "aadhar",
    "aadhaar",
    "pan",
    "ifsc",
}

# Keep it conservative; we want neutral, family-safe filler.
_BLOCKLIST = {
    "kill",
    "suicide",
    "rape",
    "porn",
    "nazi",
    "hitler",
    "terrorist",
}


def _norm_text(s: str) -> str:
    s = (s or "").strip()
    s = _RE_WS.sub(" ", s)
    return s


def _tokenize(s: str) -> list[str]:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s']", " ", s)
    s = _RE_WS.sub(" ", s).strip()
    if not s:
        return []
    toks = [t for t in s.split(" ") if t and len(t) >= 3]
    return toks[:64]


def _is_safe_bridge(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if len(t) < 25:  # avoid 1-2 word acknowledgements
        return False
    if _RE_URL.search(t) or _RE_EMAIL.search(t) or _RE_PHONE.search(t):
        return False
    low = t.lower()
    if any(w in low for w in _BLOCKLIST):
        return False
    toks = set(_tokenize(low))
    if toks.intersection(_SENSITIVE_TOKENS):
        return False
    return True


@dataclass(frozen=True)
class DialogExample:
    text: str
    source: str


class DialogBank:
    """
    Loads a large JSONL bank of neutral conversation lines and returns a "bridge" sentence
    that adds variety without changing the scam-playbook intent.
    """

    def __init__(self, examples: list[DialogExample], index: dict[str, list[int]]):
        self._examples = examples
        self._index = index

    @classmethod
    def from_jsonl(cls, path: str, max_lines: int = 50000) -> "DialogBank":
        examples: list[DialogExample] = []
        index: dict[str, list[int]] = {}

        read = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if read >= max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue

                text = obj.get("text")
                if not isinstance(text, str):
                    continue
                text = _norm_text(text)
                if not _is_safe_bridge(text):
                    continue

                src = obj.get("dataset") or obj.get("source") or "hf"
                if not isinstance(src, str):
                    src = "hf"

                ex = DialogExample(text=text, source=src)
                idx = len(examples)
                examples.append(ex)

                for tok in set(_tokenize(text)):
                    index.setdefault(tok, []).append(idx)

                read += 1

        return cls(examples=examples, index=index)

    def pick_bridge(self, *, query: str, recent_texts: set[str]) -> str | None:
        if not self._examples:
            return None

        q_toks = set(_tokenize(query))
        cand_ids: set[int] = set()
        for t in list(q_toks)[:20]:
            for i in self._index.get(t, [])[:200]:
                cand_ids.add(i)

        if not cand_ids:
            # Fallback: uniform sample
            for _ in range(15):
                ex = random.choice(self._examples)
                if ex.text not in recent_texts:
                    return ex.text
            return None

        # Score with a tiny Jaccard; keep it cheap.
        best: tuple[float, str] | None = None
        for i in random.sample(list(cand_ids), k=min(80, len(cand_ids))):
            ex = self._examples[i]
            if ex.text in recent_texts:
                continue
            ex_toks = set(_tokenize(ex.text))
            if not ex_toks:
                continue
            inter = len(q_toks & ex_toks)
            union = len(q_toks | ex_toks) or 1
            score = inter / union
            if best is None or score > best[0]:
                best = (score, ex.text)
        return best[1] if best else None


_BANK: DialogBank | None = None


def get_bank() -> DialogBank | None:
    """
    Lazy-load: avoids startup crashes on Render/free-tier.
    Controlled by env:
      DIALOG_BANK_PATH: path to JSONL (output from scripts/pull_hf_dialogs.py)
      DIALOG_BANK_MAX_LINES: int (default 50000)
    """
    global _BANK
    if _BANK is not None:
        return _BANK

    path = (os.getenv("DIALOG_BANK_PATH") or "").strip()
    if not path:
        return None
    if not os.path.exists(path):
        return None

    try:
        max_lines = int(os.getenv("DIALOG_BANK_MAX_LINES") or "50000")
    except Exception:
        max_lines = 50000
    max_lines = max(1000, min(max_lines, 200000))

    try:
        _BANK = DialogBank.from_jsonl(path, max_lines=max_lines)
    except Exception:
        _BANK = None
    return _BANK


def maybe_inject_bridge(
    *,
    base_reply: str,
    scammer_text: str,
    recent_messages: Iterable[str],
    probability: float,
) -> str:
    """
    Append 1 neutral bridge sentence, occasionally, to reduce repetition.
    Never changes the core "ask/hold/obstacle" semantics in the base reply.
    """
    if probability <= 0:
        return base_reply
    if random.random() > probability:
        return base_reply

    bank = get_bank()
    if bank is None:
        return base_reply

    base = (base_reply or "").strip()
    if not base:
        return base_reply

    # Avoid turning short, crisp replies into walls of text.
    if len(base.split()) >= 45:
        return base_reply

    recent_set = {(_norm_text(t)) for t in recent_messages if isinstance(t, str)}
    bridge = bank.pick_bridge(query=scammer_text or "", recent_texts=recent_set)
    if not bridge:
        return base_reply

    # Ensure punctuation looks natural.
    if not base.endswith((".", "!", "?")):
        base += "."
    return f"{base} {bridge}"

