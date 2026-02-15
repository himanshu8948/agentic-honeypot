import json
import os
import random
import re
from dataclasses import dataclass
from typing import Any


_WORD_RE = re.compile(r"[a-z0-9@._+-]+", re.IGNORECASE)
_STOP = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "to",
    "of",
    "and",
    "or",
    "in",
    "on",
    "for",
    "with",
    "your",
    "you",
    "we",
    "i",
    "me",
    "my",
    "sir",
    "madam",
    "please",
    "kindly",
    "now",
    "today",
}


@dataclass(frozen=True)
class LookupHit:
    score: float
    response: str
    key: str


_CACHE: list[dict[str, Any]] | None = None


def load_lookup_table() -> list[dict[str, Any]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    items: list[dict[str, Any]] = []

    seed = os.path.join(os.path.dirname(__file__), "lookup_responses_seed.json")
    items.extend(_read_items(seed))

    extra = os.getenv("LOOKUP_RESPONSES_PATH", "").strip()
    if extra:
        items.extend(_read_items(extra))

    # Normalize entries.
    out: list[dict[str, Any]] = []
    for it in items:
        domain = str(it.get("domain", "")).strip().lower() or "generic"
        persona = str(it.get("persona", "")).strip().lower() or "*"
        language = str(it.get("language", "")).strip().lower() or "*"
        pattern = str(it.get("pattern", "")).strip()
        responses = it.get("responses", [])
        if not pattern or not isinstance(responses, list) or not responses:
            continue
        resp_clean = [str(r).strip() for r in responses if str(r).strip()]
        if not resp_clean:
            continue
        out.append(
            {
                "domain": domain,
                "persona": persona,
                "language": language,
                "pattern": pattern,
                "pattern_tokens": sorted(_tokenize(pattern)),
                "responses": resp_clean,
            }
        )

    _CACHE = out
    return out


def lookup_response(
    *,
    message: str,
    domain: str,
    persona: str,
    language: str,
    min_score: float = 0.34,
) -> LookupHit | None:
    table = load_lookup_table()
    msg_tokens = _tokenize(message)
    if not msg_tokens or not table:
        return None

    domain = (domain or "generic").strip().lower()
    persona = (persona or "*").strip().lower()
    language = (language or "*").strip().lower()

    best: LookupHit | None = None
    for it in table:
        if it["domain"] not in {domain, "*"}:
            continue
        if it["persona"] not in {persona, "*"}:
            continue
        if it["language"] not in {language, "*"}:
            continue
        pat_tokens = set(it.get("pattern_tokens") or [])
        score = _jaccard(msg_tokens, pat_tokens)
        if score < min_score:
            continue
        resp = random.choice(it["responses"])
        hit = LookupHit(score=score, response=resp, key=it["pattern"])
        if best is None or hit.score > best.score:
            best = hit

    return best


def _read_items(path: str) -> list[dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)]
        return []
    except OSError:
        return []
    except Exception:
        return []


def _tokenize(text: str) -> set[str]:
    lowered = text.strip()
    lowered = re.sub(r"^(scammer|fraudster|attacker|caller|police|officer|user|victim)\s*:\s*", "", lowered, flags=re.IGNORECASE)
    tokens = {t.lower() for t in _WORD_RE.findall(lowered)}
    return {t for t in tokens if t not in _STOP and len(t) >= 3}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    union = len(a | b)
    return inter / union

