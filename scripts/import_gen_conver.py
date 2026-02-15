"""
Import labeled conversations (Person A/B) into:
  1) a lookup-table JSON (pattern -> responses) for multi-turn consistency
  2) an extra scam phrase corpus for opening-message detection

Input:
  d:\\gen_conver_noIdentifier_1000.csv
    - columns: conversation, label (1=scam, 0=non-scam)
    - conversation format: "Person A: ... Person B: ... Person A: ..."

Outputs (repo-local):
  - app/lookup_responses_gen_1000.json
  - app/fraud_corpus_gen_1000.txt
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict


SPLIT_RE = re.compile(r"\b(Person\s+[AB]):\s*", re.IGNORECASE)


def _clean(s: str) -> str:
    s = (s or "").strip()
    s = " ".join(s.split()).strip()
    return s


def _token_score(text: str) -> int:
    t = (text or "").lower()
    score = 0
    # High-signal scam tokens
    for k in [
        "otp",
        "pin",
        "password",
        "cvv",
        "verify",
        "verification",
        "urgent",
        "immediately",
        "click",
        "link",
        "install",
        "download",
        "teamviewer",
        "anydesk",
        "account",
        "bank",
        "upi",
        "transfer",
        "pay",
        "payment",
        "refund",
        "processing fee",
        "blocked",
        "suspended",
        "police",
        "arrest",
        "warrant",
    ]:
        if k in t:
            score += 2
    if any(k in t for k in ["send", "share", "provide", "confirm"]):
        score += 2
    return score


def _detect_domain(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["teamviewer", "anydesk", "remote access", "virus", "malware", "microsoft", "apple"]):
        return "tech_support"
    if any(k in t for k in ["otp", "one time password", "pin", "password", "cvv"]):
        return "otp"
    if any(k in t for k in ["upi", "@upi", "transfer", "pay", "payment", "send money", "collect request"]):
        return "upi_security"
    if any(k in t for k in ["refund", "cashback", "discount", "chargeback", "reversal"]):
        return "refund"
    if any(k in t for k in ["loan", "pre-approved", "processing fee", "interest rate"]):
        return "government_grant"
    if any(k in t for k in ["winner", "lottery", "lucky draw", "prize", "mega draw", "congratulations"]):
        return "prize_lottery"
    if any(k in t for k in ["police", "arrest", "warrant", "legal action", "investigation"]):
        return "police_authority"
    if any(k in t for k in ["blocked", "suspended", "kyc", "verify your identity", "bank", "account"]):
        return "bank_fraud"
    return "generic"


def _parse_turns(conversation: str) -> list[tuple[str, str]]:
    """
    Returns list of (speaker, text) with speaker in {"A","B"}.
    """
    s = _clean(conversation)
    if not s:
        return []
    parts = SPLIT_RE.split(s)
    # split() returns: [pre, speaker, text, speaker, text, ...]
    out: list[tuple[str, str]] = []
    i = 1
    while i + 1 < len(parts):
        spk = parts[i].strip().lower()
        txt = _clean(parts[i + 1])
        who = "A" if "a" in spk else "B"
        if txt:
            out.append((who, txt))
        i += 2
    return out


def main() -> int:
    in_path = os.getenv("GEN_CONVER_CSV", r"d:\gen_conver_noIdentifier_1000.csv").strip()
    if not os.path.exists(in_path):
        raise SystemExit(f"Missing input: {in_path}")

    out_lookup = os.getenv("OUT_LOOKUP_JSON", os.path.join("app", "lookup_responses_gen_1000.json")).strip()
    out_corpus = os.getenv("OUT_CORPUS_TXT", os.path.join("app", "fraud_corpus_gen_1000.txt")).strip()

    # Aggregate: pattern -> set(responses)
    by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    corpus_lines: set[str] = set()

    with open(in_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        for row in r:
            label = str(row.get("label") or "").strip()
            if label != "1":
                continue
            turns = _parse_turns(row.get("conversation") or "")
            if len(turns) < 2:
                continue

            # Pick scammer side by keyword score across their turns.
            score_a = sum(_token_score(t) for who, t in turns if who == "A")
            score_b = sum(_token_score(t) for who, t in turns if who == "B")
            scammer = "A" if score_a >= score_b else "B"
            victim = "B" if scammer == "A" else "A"

            # Add scammer lines to corpus and create adjacent pairs for lookup.
            for idx, (who, text) in enumerate(turns):
                if who != scammer:
                    continue
                corpus_lines.add(text)
                # response is the immediate next victim line (if any)
                if idx + 1 < len(turns) and turns[idx + 1][0] == victim:
                    resp = turns[idx + 1][1]
                    if resp:
                        domain = _detect_domain(text)
                        by_key[(domain, text)].add(resp)

    # Write corpus
    os.makedirs(os.path.dirname(out_corpus) or ".", exist_ok=True)
    with open(out_corpus, "w", encoding="utf-8") as f:
        for line in sorted(corpus_lines, key=lambda x: x.lower()):
            f.write(line + "\n")

    # Write lookup items
    items: list[dict[str, object]] = []
    for (domain, pattern), resps in by_key.items():
        if not pattern or not resps:
            continue
        items.append(
            {
                "domain": domain,
                "persona": "*",
                "language": "en",
                "pattern": pattern,
                "responses": sorted(resps, key=lambda x: x.lower())[:8],
            }
        )

    os.makedirs(os.path.dirname(out_lookup) or ".", exist_ok=True)
    with open(out_lookup, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=True, indent=2)

    print(f"Wrote lookup items: {len(items)} -> {out_lookup}")
    print(f"Wrote corpus lines: {len(corpus_lines)} -> {out_corpus}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

