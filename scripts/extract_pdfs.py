from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "rag" / "papers"
OUT_DIR = SRC_DIR / "cleaned"

SOURCES = [
    "crossing-margins.pdf",
    "along-the-margins.pdf",
    "beyond-keywords.pdf",
    "the-best-ends-by-the-best-means.pdf",
]

def extract(pdf_path: Path) -> str:
    doc = pymupdf.open(pdf_path)
    parts: list[str] = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if not text:
            continue
        parts.append(f"<!-- page {i} -->\n\n{text}\n")
    doc.close()
    return "\n".join(parts)

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    missing = [s for s in SOURCES if not (SRC_DIR / s).exists()]
    if missing:
        print(f"missing PDFs: {missing}", file=sys.stderr)
        return 1

    for src in SOURCES:
        pdf_path = SRC_DIR / src
        out_path = OUT_DIR / f"{pdf_path.stem}.md"
        body = extract(pdf_path)
        header = (
            f"# {pdf_path.stem}\n\n"
            "> **Status:** raw pymupdf extraction. Hand-cleanup required before chunking.\n"
            "> See `rag/papers/cleaned/README.md` for the cleanup checklist.\n\n"
        )
        out_path.write_text(header + body, encoding="utf-8")
        print(f"wrote {out_path.relative_to(ROOT)} ({len(body):,} chars)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
