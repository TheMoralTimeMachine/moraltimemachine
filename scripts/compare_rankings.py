from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COSINE_PATH = ROOT / "tests/golden_retrieval_cosine.json"
RERANK_PATH = ROOT / "tests/golden_retrieval.json"

def main() -> int:
    if not COSINE_PATH.exists():
        print(f"missing baseline: {COSINE_PATH}")
        return 1
    if not RERANK_PATH.exists():
        print(f"missing current golden: {RERANK_PATH} (run pytest --regen-golden)")
        return 1

    cosine = json.loads(COSINE_PATH.read_text())
    rerank = json.loads(RERANK_PATH.read_text())

    total_overlap = 0
    total_slots = 0
    for name in cosine:
        cos = cosine[name]["expected"]
        new = rerank.get(name, {}).get("expected", [])
        print(f"\n=== {name} ===")
        print(f"query: {cosine[name]['query']!r}")
        print(f"{'rank':<5} {'cosine':<42} {'cross-encoder':<42} changed?")
        for i in range(max(len(cos), len(new))):
            c = cos[i] if i < len(cos) else "-"
            n = new[i] if i < len(new) else "-"
            marker = "" if c == n else "  <-- diff"
            print(f"{i+1:<5} {c:<42} {n:<42}{marker}")
        overlap = set(cos) & set(new)
        print(f"set overlap: {len(overlap)}/{len(cos)} chunks shared")
        total_overlap += len(overlap)
        total_slots += len(cos)

    print(f"\n--- summary ---")
    print(f"overall set overlap: {total_overlap}/{total_slots} top-k slots")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
