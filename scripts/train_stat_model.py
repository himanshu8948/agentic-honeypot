import ast
import csv
import json
import math
import os
import re
from collections import Counter


TOKEN_RE = re.compile(r"[a-z0-9@._/-]{2,}", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def _extract_texts(cell: str) -> list[str]:
    s = (cell or "").strip()
    if not s:
        return []
    # Many fields are serialized python lists like: ["a" 'b'] or ['a', 'b']
    try:
        v = ast.literal_eval(s)
        if isinstance(v, (list, tuple)):
            out: list[str] = []
            for item in v:
                if isinstance(item, str):
                    t = item.strip()
                    if t:
                        out.append(t)
            return out
        if isinstance(v, str):
            return [v.strip()] if v.strip() else []
    except Exception:
        pass

    # Fallback: grab quoted substrings
    out = re.findall(r"['\"]([^'\"]{5,4000})['\"]", s)
    return [t.strip() for t in out if t.strip()] or ([s] if len(s) <= 4000 else [s[:4000]])


def build_training_corpus(*, scam_csv: str, ham_csv: str, max_ham: int = 25000) -> tuple[list[str], list[int]]:
    xs: list[str] = []
    ys: list[int] = []

    # Scam positives
    with open(scam_csv, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        for row in r:
            msg = (row.get("message") or "").strip()
            if msg:
                xs.append(msg)
                ys.append(1)

    # Extra scam scripts (txt)
    scam_txt = (os.getenv("SCAM_TXT") or "").strip()
    if not scam_txt:
        for cand in [r"d:\English_Scam.txt", r"d:\agentic-ai\data\scam_import\English_Scam.txt"]:
            if os.path.exists(cand):
                scam_txt = cand
                break
    if scam_txt and os.path.exists(scam_txt):
        with open(scam_txt, "r", encoding="utf-8", errors="replace") as f:
            for ln in f:
                t = ln.strip()
                if 10 <= len(t) <= 2000:
                    xs.append(t)
                    ys.append(1)

    # Ham negatives from dialogue dataset
    ham_texts: list[str] = []
    if ham_csv and os.path.exists(ham_csv):
        with open(ham_csv, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.DictReader(f)
            for row in r:
                for col in ["previous_utterance", "free_messages", "guided_messages", "suggestions"]:
                    for t in _extract_texts(row.get(col) or ""):
                        if 10 <= len(t) <= 2000:
                            ham_texts.append(t)

    # Extra ham scripts (txt)
    ham_txt = (os.getenv("HAM_TXT") or "").strip()
    if not ham_txt:
        for cand in [r"d:\English_NonScam.txt", r"d:\agentic-ai\data\scam_import\English_NonScam.txt"]:
            if os.path.exists(cand):
                ham_txt = cand
                break
    if ham_txt and os.path.exists(ham_txt):
        with open(ham_txt, "r", encoding="utf-8", errors="replace") as f:
            for ln in f:
                t = ln.strip()
                if 10 <= len(t) <= 2000:
                    ham_texts.append(t)

    # Downsample deterministically.
    ham_texts = ham_texts[: max_ham]
    for t in ham_texts:
        xs.append(t)
        ys.append(0)

    return xs, ys


def train_naive_bayes(xs: list[str], ys: list[int], vocab_size: int = 50000, alpha: float = 1.0) -> dict:
    scam_counts = Counter()
    ham_counts = Counter()
    scam_docs = 0
    ham_docs = 0

    for text, y in zip(xs, ys):
        toks = _tokens(text)
        if not toks:
            continue
        if y == 1:
            scam_docs += 1
            scam_counts.update(toks)
        else:
            ham_docs += 1
            ham_counts.update(toks)

    # Build vocab by overall frequency.
    total = scam_counts + ham_counts
    vocab = {t for t, _ in total.most_common(vocab_size)}

    scam_total = sum(scam_counts[t] for t in vocab)
    ham_total = sum(ham_counts[t] for t in vocab)
    V = max(1, len(vocab))

    def _logp(count: int, tot: int) -> float:
        return math.log((count + alpha) / (tot + alpha * V))

    logp_scam = {t: _logp(scam_counts[t], scam_total) for t in vocab}
    logp_ham = {t: _logp(ham_counts[t], ham_total) for t in vocab}

    log_prior_scam = math.log((scam_docs + 1) / (scam_docs + ham_docs + 2))
    log_prior_ham = math.log((ham_docs + 1) / (scam_docs + ham_docs + 2))

    model = {
        "log_prior_scam": log_prior_scam,
        "log_prior_ham": log_prior_ham,
        "logp_token_scam": logp_scam,
        "logp_token_ham": logp_ham,
        "logp_unk_scam": _logp(0, scam_total),
        "logp_unk_ham": _logp(0, ham_total),
        "meta": {
            "vocab_size": len(vocab),
            "alpha": alpha,
            "scam_docs": scam_docs,
            "ham_docs": ham_docs,
        },
    }
    return model


def main() -> None:
    scam_csv = os.getenv("SCAM_CSV", r"d:\scam_dataset.csv")
    ham_csv = os.getenv("HAM_CSV", r"d:\train.csv")
    out_path = os.getenv("OUT_MODEL", r"models\scam_nb.json")

    xs, ys = build_training_corpus(scam_csv=scam_csv, ham_csv=ham_csv)
    model = train_naive_bayes(xs, ys)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(model, f)
    print(f"Wrote model: {out_path} (vocab={model['meta']['vocab_size']})")


if __name__ == "__main__":
    main()
