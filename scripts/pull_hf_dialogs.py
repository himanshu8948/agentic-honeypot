"""
Pull conversations/utterances from Hugging Face datasets via the datasets-server API
without installing heavy dependencies.

This script writes JSONL with one utterance per line:
  {"dataset": "...", "config": "...", "split": "...", "row": 123, "turn": 0, "text": "..."}

Usage (PowerShell):
  python scripts/pull_hf_dialogs.py --out data/hf_utterances.jsonl --max-utterances 100000
"""

from __future__ import annotations

import argparse
import json
import os
import time
import hashlib
from typing import Any, Iterable

import httpx


HF_SERVER = "https://datasets-server.huggingface.co"


def _iter_utterances_from_row(row: dict[str, Any]) -> Iterable[str]:
    # Try common conversation schemas.
    for key in ["dialog", "dialogue", "utterances", "messages", "conversation", "turns"]:
        v = row.get(key)
        if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
            for s in v:
                t = " ".join(s.split()).strip()
                if t:
                    yield t
            return
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            for m in v:
                for ck in ["text", "utterance", "content"]:
                    if isinstance(m.get(ck), str):
                        t = " ".join(m[ck].split()).strip()
                        if t:
                            yield t
            return

    # Single-utterance schemas.
    for key in ["text", "utterance", "sentence", "context", "message"]:
        v = row.get(key)
        if isinstance(v, str):
            t = " ".join(v.split()).strip()
            if t:
                yield t
            return


def _get_json(client: httpx.Client, path: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{HF_SERVER}{path}"
    r = client.get(url, params=params)
    r.raise_for_status()
    return r.json()


def _splits(client: httpx.Client, dataset: str) -> list[tuple[str, str]]:
    """
    datasets-server exposes dataset configs and splits via /splits.
    Response example:
      {"splits":[{"dataset":"...","config":"default","split":"train"}], ...}
    """
    data = _get_json(client, "/splits", {"dataset": dataset})
    out: list[tuple[str, str]] = []
    for s in (data.get("splits") or []):
        cfg = s.get("config")
        sp = s.get("split")
        if isinstance(cfg, str) and cfg and isinstance(sp, str) and sp:
            out.append((cfg, sp))
    return out


def _rows(
    client: httpx.Client,
    dataset: str,
    config: str,
    split: str,
    offset: int,
    length: int,
) -> list[dict[str, Any]]:
    data = _get_json(
        client,
        "/rows",
        {"dataset": dataset, "config": config, "split": split, "offset": offset, "length": length},
    )
    out = []
    for r in (data.get("rows") or []):
        row = r.get("row")
        if isinstance(row, dict):
            out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-utterances", type=int, default=100000)
    ap.add_argument("--batch", type=int, default=100, help="rows per request (datasets-server max is 100)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--append", action="store_true", help="append to existing file instead of overwriting")
    ap.add_argument("--dedupe", action="store_true", default=True, help="skip duplicate utterances (recommended)")
    ap.add_argument("--sleep", type=float, default=0.15, help="base sleep between requests (seconds)")
    ap.add_argument(
        "--datasets",
        default="allenai/WildChat-1M,HuggingFaceH4/ultrachat_200k,OpenAssistant/oasst1,teknium/OpenHermes-2.5",
        help="Comma-separated HF dataset IDs",
    )
    args = ap.parse_args()

    wanted = max(1, int(args.max_utterances))
    batch = max(10, min(100, int(args.batch)))
    datasets = [d.strip() for d in str(args.datasets).split(",") if d.strip()]

    wrote = 0
    seen: set[bytes] = set()
    mode = "a" if args.append else "w"
    if args.append and os.path.exists(args.out):
        # Count and seed the dedupe set from existing file so "resume" doesn't balloon.
        with open(args.out, "r", encoding="utf-8") as rf:
            for line in rf:
                wrote += 1
                if args.dedupe:
                    try:
                        obj = json.loads(line)
                        txt = obj.get("text")
                        if isinstance(txt, str):
                            seen.add(hashlib.blake2b(txt.encode("utf-8"), digest_size=8).digest())
                    except Exception:
                        pass

    sleep_s = max(0.01, float(args.sleep))

    with httpx.Client(timeout=30) as client, open(args.out, mode, encoding="utf-8") as f:
        for ds in datasets:
            try:
                cfg_splits = _splits(client, ds)
            except Exception as e:
                if args.verbose:
                    print(f"[skip] splits failed for {ds}: {e}")
                continue

            for cfg, split in cfg_splits:
                offset = 0
                backoff = 0.0
                while wrote < wanted:
                    try:
                        rows = _rows(client, ds, cfg, split, offset, batch)
                    except Exception as e:
                        msg = str(e)
                        if "429" in msg:
                            backoff = max(1.0, backoff * 1.8) if backoff else 2.0
                            if args.verbose:
                                print(f"[429] backing off {backoff:.1f}s for {ds} {cfg}/{split} @ {offset}")
                            time.sleep(backoff)
                            continue
                        if args.verbose:
                            print(f"[stop] rows failed for {ds} {cfg}/{split} @ {offset}: {e}")
                        break
                    if not rows:
                        break

                    for i, row in enumerate(rows):
                        for turn, utt in enumerate(_iter_utterances_from_row(row)):
                            if args.dedupe:
                                h = hashlib.blake2b(utt.encode("utf-8"), digest_size=8).digest()
                                if h in seen:
                                    continue
                                seen.add(h)
                            rec = {"dataset": ds, "config": cfg, "split": split, "row": offset + i, "turn": turn, "text": utt}
                            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
                            wrote += 1
                            if wrote >= wanted:
                                break
                        if wrote >= wanted:
                            break

                    offset += len(rows)
                    if offset % (batch * 10) == 0:
                        f.flush()
                    # be gentle to the public API
                    time.sleep(sleep_s + (backoff * 0.15))
                if wrote >= wanted:
                    break
            if wrote >= wanted:
                break

    print(f"Wrote {wrote} utterances to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
