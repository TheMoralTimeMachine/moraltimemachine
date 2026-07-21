from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = "data/mtm.sqlite3"

_SESSION_COLUMNS_SLIM = "id, participant_key, speed, description, feature_title, created_at"

_EXPORTS = {
    "participants.csv": "SELECT * FROM participants ORDER BY created_at",
    "sessions.csv": f"SELECT {_SESSION_COLUMNS_SLIM} FROM sessions ORDER BY created_at",
    "chat_messages.csv": "SELECT * FROM chat_messages ORDER BY session_id, id",
    "feedback.csv": "SELECT * FROM feedback ORDER BY created_at",
}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB, help=f"database path (default: {DEFAULT_DB})")
    parser.add_argument("--out", default="data/export", help="output directory (default: data/export)")
    parser.add_argument(
        "--full", action="store_true", help="include reflections/stakeholders JSON in sessions.csv"
    )
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"database not found: {args.db}", file=sys.stderr)
        return 1

    exports = dict(_EXPORTS)
    if args.full:
        exports["sessions.csv"] = "SELECT * FROM sessions ORDER BY created_at"

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    try:
        for filename, query in exports.items():
            cur = conn.execute(query)
            path = out_dir / filename
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([d[0] for d in cur.description])
                rows = cur.fetchall()
                writer.writerows(rows)
            print(f"{path} ({len(rows)} rows)")
    finally:
        conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
