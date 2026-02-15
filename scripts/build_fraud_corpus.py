"""
Build/refresh a larger scam phrase corpus used by app/fraud_corpus.py.

Goal: improve first-layer matching without any online LLMs.

Inputs (optional):
  - SCAM_CSV: CSV with a 'message' column (default d:\\scam_dataset.csv)
  - SCAM_TXT: plain-text file with one scam script per line (default d:\\English_Scam.txt if exists)

Output:
  - app/fraud_corpus_extra.txt

This file is intentionally capped to keep repo/runtime lightweight.
"""

from __future__ import annotations

import csv
import os
import re


RE_NUM_PREFIX = re.compile(r"^\s*\d+\.\s*")


def _clean_line(s: str) -> str:
    s = (s or "").strip()
    s = RE_NUM_PREFIX.sub("", s)
    s = " ".join(s.split()).strip()
    return s


def _read_scam_csv(path: str) -> list[str]:
    out: list[str] = []
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.DictReader(f)
            for row in r:
                msg = _clean_line(row.get("message") or "")
                if msg:
                    out.append(msg)
    except OSError:
        return []
    return out


def _read_lines(path: str) -> list[str]:
    out: list[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for ln in f:
                s = _clean_line(ln)
                if s:
                    out.append(s)
    except OSError:
        return []
    return out


def main() -> int:
    scam_csv = os.getenv("SCAM_CSV", r"d:\scam_dataset.csv").strip()
    scam_txt = os.getenv("SCAM_TXT", "").strip()
    if not scam_txt:
        # Common local paths in this workspace
        for cand in [r"d:\English_Scam.txt", r"d:\agentic-ai\data\scam_import\English_Scam.txt"]:
            if os.path.exists(cand):
                scam_txt = cand
                break

    max_lines = int(os.getenv("FRAUD_CORPUS_BUILD_MAX_LINES", "5000"))
    max_lines = max(500, min(max_lines, 50000))

    lines: list[str] = []
    lines.extend(_read_scam_csv(scam_csv))
    if scam_txt:
        lines.extend(_read_lines(scam_txt))

    seen: set[str] = set()
    deduped: list[str] = []
    for s in lines:
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(s)
        if len(deduped) >= max_lines:
            break

    out_path = os.path.join("app", "fraud_corpus_extra.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for s in deduped:
            f.write(s + "\n")

    print(f"Wrote {len(deduped)} lines -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

