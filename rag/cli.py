from __future__ import annotations

import argparse
import json
import logging
import sys
import textwrap

from rag.retriever import DEFAULT_SCORING, EmptyRetrievalError, QueryTooLargeError, retrieve

SNIPPET_CHARS = 280

def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return parts or None

def _format_chunk(idx: int, chunk, *, full: bool) -> str:
    body = chunk.body if full else textwrap.shorten(chunk.body, width=SNIPPET_CHARS, placeholder=" …")
    indented = textwrap.indent(body, "    ")
    return (
        f"[{idx}] {chunk.chunk_id}  (sim={chunk.similarity:.3f})\n"
        f"    source:      {chunk.source}\n"
        f"    type:        {chunk.chunk_type}\n"
        f"    harm_labels: {', '.join(chunk.harm_labels) or '-'}\n"
        f"    body:\n{indented}\n"
    )

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="rag.cli",
        description="Ad-hoc query against the RAG retriever.",
    )
    p.add_argument("query", help="Feature description / search string")
    p.add_argument("-k", type=int, default=5, help="Number of results (default 5)")
    p.add_argument(
        "--types", "-t",
        help="Comma-separated chunk_types filter, e.g. real-incident,qualitative-finding",
    )
    p.add_argument(
        "--labels", "-l",
        help="Comma-separated Spectrum harm_labels filter, e.g. Privacy,Disparity",
    )
    p.add_argument(
        "--scoring", "-s",
        choices=["cosine", "cross-encoder"],
        default=DEFAULT_SCORING,
        help=f"Scoring method (default: {DEFAULT_SCORING})",
    )
    p.add_argument("--full", action="store_true", help="Print full chunk bodies (no snippet)")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of pretty text")
    p.add_argument("-v", "--verbose", action="store_true", help="Show retriever INFO logs")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        chunks = retrieve(
            args.query,
            k=args.k,
            chunk_types=_split_csv(args.types),
            harm_labels=_split_csv(args.labels),
            scoring_method=args.scoring,
        )
    except QueryTooLargeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except EmptyRetrievalError as e:
        print(f"no results: {e}", file=sys.stderr)
        return 1

    if args.json:
        payload = [
            {
                "chunk_id": c.chunk_id,
                "source": c.source,
                "source_full_title": c.source_full_title,
                "chunk_type": c.chunk_type,
                "harm_labels": c.harm_labels,
                "similarity": round(c.similarity, 4),
                "body": c.body,
            }
            for c in chunks
        ]
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print(f"query: {args.query!r}")
    filters = []
    if args.types:
        filters.append(f"types={args.types}")
    if args.labels:
        filters.append(f"labels={args.labels}")
    print(f"k={args.k}" + (f"  filters: {', '.join(filters)}" if filters else ""))
    print(f"returned {len(chunks)} chunk(s)\n")
    for i, c in enumerate(chunks, start=1):
        print(_format_chunk(i, c, full=args.full))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
