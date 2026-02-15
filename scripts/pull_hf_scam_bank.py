"""
Pull scam/spam messages (and scammer-side turns from scam-dialog datasets) from
Hugging Face via the datasets-server API.

This is for:
  - improving first-message detection corpora
  - generating lookup patterns (scammer prompt -> victim reply) from dialogs

It does NOT require `datasets`/`pyarrow`.

Output JSONL schema (one record per scam/spam message):
  {
    "dataset": "...",
    "config": "...",
    "split": "...",
    "row": 123,
    "kind": "sms|email|dialog_turn",
    "scam_type": "...",
    "label": "spam|ham|unknown",
    "text": "..."
  }

Examples:
  python scripts/pull_hf_scam_bank.py --out data/scam_bank.jsonl --max 100000
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import hashlib
from typing import Any, Iterable

import httpx


HF_SERVER = "https://datasets-server.huggingface.co"
WS_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = WS_RE.sub(" ", s)
    return s


def _get_json(client: httpx.Client, path: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{HF_SERVER}{path}"
    r = client.get(url, params=params)
    r.raise_for_status()
    return r.json()


def _splits(client: httpx.Client, dataset: str) -> list[tuple[str, str]]:
    data = _get_json(client, "/splits", {"dataset": dataset})
    out: list[tuple[str, str]] = []
    for s in (data.get("splits") or []):
        cfg = s.get("config")
        sp = s.get("split")
        if isinstance(cfg, str) and cfg and isinstance(sp, str) and sp:
            out.append((cfg, sp))
    return out


def _rows(client: httpx.Client, dataset: str, config: str, split: str, offset: int, length: int) -> list[dict[str, Any]]:
    data = _get_json(
        client,
        "/rows",
        {"dataset": dataset, "config": config, "split": split, "offset": offset, "length": length},
    )
    out: list[dict[str, Any]] = []
    for r in (data.get("rows") or []):
        row = r.get("row")
        if isinstance(row, dict):
            out.append(row)
    return out


def _as_label(v: Any) -> str:
    if isinstance(v, bool):
        return "spam" if v else "ham"
    if isinstance(v, (int, float)):
        return "spam" if int(v) == 1 else "ham"
    if isinstance(v, str):
        t = v.strip().lower()
        if t in {"spam", "scam", "phishing"}:
            return "spam"
        if t in {"ham", "legit", "normal"}:
            return "ham"
        if t in {"1", "true", "yes"}:
            return "spam"
        if t in {"0", "false", "no"}:
            return "ham"
    return "unknown"


def _join_text(value: Any) -> str:
    if isinstance(value, str):
        return _norm(value)
    if isinstance(value, list):
        parts = []
        for x in value:
            if isinstance(x, str) and x.strip():
                parts.append(x.strip())
        return _norm("\n".join(parts))
    return ""


def _iter_scam_texts(dataset: str, row: dict[str, Any]) -> Iterable[tuple[str, str, str]]:
    """
    Yields tuples: (kind, label, text)
    """
    ds = dataset.lower()

    # SMS spam collections
    if dataset in {"codesignal/sms-spam-collection"}:
        label = _as_label(row.get("label"))
        msg = _join_text(row.get("message"))
        if msg:
            yield ("sms", label, msg)
        return
    if dataset in {"ucirvine/sms_spam"}:
        label = _as_label(row.get("label"))
        msg = _join_text(row.get("sms"))
        if msg:
            yield ("sms", label, msg)
        return

    # Enron spam (email lines list)
    if dataset in {"bvk/ENRON-spam"}:
        label = _as_label(row.get("label"))
        msg = _join_text(row.get("email"))
        if msg:
            yield ("email", label, msg)
        return

    # AlignmentResearch EnronSpam (content list, clf_label)
    if dataset in {"AlignmentResearch/EnronSpam"}:
        label = _as_label(row.get("clf_label"))
        msg = _join_text(row.get("content"))
        if msg:
            yield ("email", label, msg)
        return

    # Scam conversations (dialogue string with Suspect/Innocent)
    if dataset in {"BothBosu/multi-agent-scam-conversation", "BothBosu/youtube-scam-conversations"}:
        # Labels are int (0/1). Treat as spam if ==1 else unknown.
        label = _as_label(row.get("labels"))
        dialogue = _join_text(row.get("dialogue"))
        if not dialogue:
            return
        # Extract only Suspect turns as "scammer messages"
        for m in re.finditer(r"\bSuspect:\s*([^\\n]+)", dialogue, flags=re.IGNORECASE):
            t = _norm(m.group(1))
            if t:
                yield ("dialog_turn", label, t)
        return

    # SMS sample 10k (phishing boolean + sms_text)
    if dataset in {"gandharvbakshi/SMS-dataset-sample-10k"}:
        label = _as_label(row.get("is_phishing_original"))
        msg = _join_text(row.get("sms_text"))
        if msg:
            yield ("sms", label, msg)
        return

    # Generic fallback: try common names
    label = _as_label(row.get("label"))
    for key in ("text", "message", "sms", "content"):
        msg = _join_text(row.get(key))
        if msg:
            yield ("unknown", label, msg)
            return


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=100000)
    ap.add_argument("--batch", type=int, default=100)
    ap.add_argument("--sleep", type=float, default=0.2)
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--keep-ham", action="store_true", help="also keep ham (default: only spam)")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument(
        "--datasets",
        default="ucirvine/sms_spam,codesignal/sms-spam-collection,gandharvbakshi/SMS-dataset-sample-10k,bvk/ENRON-spam,AlignmentResearch/EnronSpam,BothBosu/multi-agent-scam-conversation",
    )
    args = ap.parse_args()

    wanted = max(1, int(args.max))
    batch = max(10, min(100, int(args.batch)))
    sleep_s = max(0.01, float(args.sleep))
    datasets = [d.strip() for d in str(args.datasets).split(",") if d.strip()]

    mode = "a" if args.append else "w"
    wrote = 0
    seen: set[bytes] = set()
    if args.append and os.path.exists(args.out):
        with open(args.out, "r", encoding="utf-8", errors="replace") as rf:
            for line in rf:
                wrote += 1
                try:
                    obj = json.loads(line)
                    txt = obj.get("text")
                    if isinstance(txt, str) and txt:
                        seen.add(hashlib.blake2b(txt.encode("utf-8"), digest_size=8).digest())
                except Exception:
                    pass

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
                                print(f"[429] {ds} backoff {backoff:.1f}s")
                            time.sleep(backoff)
                            continue
                        if args.verbose:
                            print(f"[stop] rows failed for {ds} {cfg}/{split} @ {offset}: {e}")
                        break

                    if not rows:
                        break

                    for i, row in enumerate(rows):
                        for kind, label, text in _iter_scam_texts(ds, row):
                            if not text:
                                continue
                            if label != "spam" and not args.keep_ham:
                                continue
                            h = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
                            if h in seen:
                                continue
                            seen.add(h)
                            rec = {
                                "dataset": ds,
                                "config": cfg,
                                "split": split,
                                "row": offset + i,
                                "kind": kind,
                                "label": label,
                                "scam_type": str(row.get("type") or row.get("scam_type") or "").strip(),
                                "text": text,
                            }
                            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
                            wrote += 1
                            if wrote >= wanted:
                                break
                        if wrote >= wanted:
                            break

                    offset += len(rows)
                    if offset % (batch * 10) == 0:
                        f.flush()
                    time.sleep(sleep_s + (backoff * 0.15))

                    if wrote >= wanted:
                        break
                if wrote >= wanted:
                    break
            if wrote >= wanted:
                break

    print(f"Wrote {wrote} scam/spam messages -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

