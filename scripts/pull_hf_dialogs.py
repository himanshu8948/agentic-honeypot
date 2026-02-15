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
import time
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


def _configs(client: httpx.Client, dataset: str) -> list[str]:
    data = _get_json(client, "/configs", {"dataset": dataset})
    return [c["config"] for c in (data.get("configs") or []) if "config" in c]


def _splits(client: httpx.Client, dataset: str, config: str) -> list[str]:
    data = _get_json(client, "/splits", {"dataset": dataset, "config": config})
    splits = []
    for s in (data.get("splits") or []):
        name = s.get("split")
        if isinstance(name, str) and name:
            splits.append(name)
    return splits


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
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument(
        "--datasets",
        default="daily_dialog,blended_skill_talk,empathetic_dialogues,wizard_of_wikipedia,conv_ai_2",
        help="Comma-separated HF dataset IDs",
    )
    args = ap.parse_args()

    wanted = max(1, int(args.max_utterances))
    batch = max(10, int(args.batch))
    datasets = [d.strip() for d in str(args.datasets).split(",") if d.strip()]

    wrote = 0
    with httpx.Client(timeout=30) as client, open(args.out, "w", encoding="utf-8") as f:
        for ds in datasets:
            try:
                cfgs = _configs(client, ds) or ["default"]
            except Exception:
                continue

            for cfg in cfgs[:3]:  # keep it bounded; many datasets have lots of configs
                try:
                    splits = _splits(client, ds, cfg) or ["train"]
                except Exception:
                    continue

                for split in splits:
                    offset = 0
                    while wrote < wanted:
                        try:
                            rows = _rows(client, ds, cfg, split, offset, batch)
                        except Exception:
                            break
                        if not rows:
                            break

                        for i, row in enumerate(rows):
                            for turn, utt in enumerate(_iter_utterances_from_row(row)):
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
                        time.sleep(0.05)  # be gentle to the public API
                    if wrote >= wanted:
                        break
                if wrote >= wanted:
                    break
            if wrote >= wanted:
                break

    print(f"Wrote {wrote} utterances to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

