from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import db

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("count", type=int, help="number of keys to mint")
    parser.add_argument("--label", default="", help="batch label, e.g. 'pilot' or 'round1'")
    parser.add_argument("--db", default=None, help=f"database path (default: {db.DB_PATH})")
    args = parser.parse_args()

    if args.count < 1:
        print("count must be >= 1", file=sys.stderr)
        return 1

    db.init(args.db)
    for key in db.mint_participants(args.count, args.label):
        print(key)
    return 0

if __name__ == "__main__":
    sys.exit(main())
