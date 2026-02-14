from __future__ import annotations

import re
import sys
from pathlib import Path

from pypdf import PdfReader


def extract_headers(pdf_path: Path) -> set[str]:
    reader = PdfReader(str(pdf_path))
    headers: set[str] = set()

    for page in reader.pages:
        text = page.extract_text() or ""
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            low = s.lower()
            if low.startswith("header principal") or low.startswith("page "):
                continue

            m = re.match(r"^([A-Za-z0-9-]{2,20})\s+.+$", s)
            if not m:
                continue

            token = m.group(1).upper()
            if token == "HEADER":
                continue

            parts = [p for p in token.split("-") if p]
            if len(parts) >= 2 and len(parts[-1]) >= 3:
                token = parts[-1]

            headers.add(token)

    return headers


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python scripts/extract_sms_headers.py <input.pdf> <output.txt>")
        return 1

    pdf = Path(sys.argv[1])
    out = Path(sys.argv[2])

    if not pdf.exists():
        print(f"Input PDF not found: {pdf}")
        return 1

    headers = sorted(extract_headers(pdf))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Auto-generated from {pdf.name}\n")
        for h in headers:
            f.write(h + "\n")

    print(f"Wrote {len(headers)} headers to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
