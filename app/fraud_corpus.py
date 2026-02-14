import os
import re
from dataclasses import dataclass


_WORD_RE = re.compile(r"[a-z0-9@._+-]+", re.IGNORECASE)


@dataclass(frozen=True)
class CorpusMatch:
    score: float
    snippet: str


def load_corpus_lines() -> list[str]:
    lines: list[str] = []

    # Seed corpus shipped with repo.
    seed_path = os.path.join(os.path.dirname(__file__), "fraud_corpus_seed.txt")
    lines.extend(_read_lines(seed_path))

    # Optional external corpus path (e.g., OCR output exported from PDF).
    extra_path = os.getenv("FRAUD_CORPUS_PATH", "").strip()
    if extra_path:
        lines.extend(_read_lines(extra_path))

    # Normalize + drop empties.
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        clean = " ".join(line.split()).strip()
        if not clean:
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)

    max_lines_raw = os.getenv("FRAUD_CORPUS_MAX_LINES", "").strip()
    if max_lines_raw:
        try:
            max_lines = int(max_lines_raw)
            if max_lines > 0:
                out = out[:max_lines]
        except Exception:
            pass

    return out


def best_match(text: str, corpus_lines: list[str]) -> CorpusMatch:
    # Fast, dependency-free similarity: token Jaccard on normalized words.
    query_tokens = _tokenize(text)
    if not query_tokens:
        return CorpusMatch(score=0.0, snippet="")

    best_score = 0.0
    best_snip = ""
    for line in corpus_lines:
        # Prefer fraudster/scammer lines if tagged.
        if _is_user_line(line):
            continue
        cand_tokens = _tokenize(line)
        if not cand_tokens:
            continue
        score = _jaccard(query_tokens, cand_tokens)
        if score > best_score:
            best_score = score
            best_snip = line

    return CorpusMatch(score=best_score, snippet=best_snip)


def _read_lines(path: str) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    except OSError:
        return []


def _tokenize(text: str) -> set[str]:
    # Remove common prefixes like "Scammer:" to reduce skew.
    lowered = text.strip()
    lowered = re.sub(r"^(scammer|fraudster|attacker|caller|user|victim)\s*:\s*", "", lowered, flags=re.IGNORECASE)
    tokens = {t.lower() for t in _WORD_RE.findall(lowered)}
    # Drop ultra-common filler tokens.
    stop = {
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
    return {t for t in tokens if t not in stop and len(t) >= 3}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    union = len(a | b)
    return inter / union


def _is_user_line(line: str) -> bool:
    return bool(re.match(r"^\s*(user|victim)\s*:", line, flags=re.IGNORECASE))

