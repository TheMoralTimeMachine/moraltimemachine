from __future__ import annotations

import csv
import io
import json
import os
import secrets
import sqlite3
import threading
from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from backend.config import DEMOGRAPHIC_IDS, LIKERT_IDS, OPEN_IDS
from backend.models import ChatMessage, Reflection

if TYPE_CHECKING:
    from backend.sessions import Session

DB_PATH = os.getenv("MTM_DB_PATH", "data/mtm.sqlite3")

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()

_reflections_adapter = TypeAdapter(list[Reflection])

_SCHEMA = """
CREATE TABLE IF NOT EXISTS participants (
  key        TEXT PRIMARY KEY,
  label      TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  id              TEXT PRIMARY KEY,
  participant_key TEXT NOT NULL REFERENCES participants(key),
  speed           TEXT NOT NULL,
  description     TEXT NOT NULL,
  feature_title   TEXT NOT NULL DEFAULT '',
  stakeholders    TEXT NOT NULL DEFAULT '{}',
  reflections     TEXT NOT NULL DEFAULT '[]',
  prolific_pid    TEXT NOT NULL DEFAULT '',
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_participant ON sessions(participant_key);

CREATE TABLE IF NOT EXISTS chat_messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  role       TEXT NOT NULL,
  content    TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id);

CREATE TABLE IF NOT EXISTS feedback (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_key     TEXT NOT NULL REFERENCES participants(key),
  mode                TEXT NOT NULL,
  session_id_fast     TEXT,
  session_id_thinking TEXT,
  likert_1 INTEGER NOT NULL CHECK (likert_1 BETWEEN 1 AND 5),
  likert_2 INTEGER NOT NULL CHECK (likert_2 BETWEEN 1 AND 5),
  likert_3 INTEGER NOT NULL CHECK (likert_3 BETWEEN 1 AND 5),
  likert_4 INTEGER NOT NULL CHECK (likert_4 BETWEEN 1 AND 5),
  likert_5 INTEGER NOT NULL CHECK (likert_5 BETWEEN 1 AND 5),
  likert_6 INTEGER NOT NULL CHECK (likert_6 BETWEEN 1 AND 5),
  likert_7 INTEGER NOT NULL CHECK (likert_7 BETWEEN 1 AND 5),
  -- Nullable on purpose: NULL = "did not use" (see config.NULLABLE_LIKERT_IDS).
  likert_8 INTEGER CHECK (likert_8 IS NULL OR likert_8 BETWEEN 1 AND 5),
  open_1 TEXT NOT NULL DEFAULT '',
  open_2 TEXT NOT NULL DEFAULT '',
  open_3 TEXT NOT NULL DEFAULT '',
  open_4 TEXT NOT NULL DEFAULT '',
  open_5 TEXT NOT NULL DEFAULT '',
  -- Demographics (see config.DEMOGRAPHIC_IDS); stored as the chosen option label
  -- or the typed free-text answer. '' when unanswered (e.g. optional gender).
  role               TEXT NOT NULL DEFAULT '',
  experience         TEXT NOT NULL DEFAULT '',
  ethics_familiarity TEXT NOT NULL DEFAULT '',
  age                TEXT NOT NULL DEFAULT '',
  gender             TEXT NOT NULL DEFAULT '',
  raw_json   TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (session_id_fast),
  UNIQUE (session_id_thinking)
);
"""

class DuplicateFeedbackError(Exception):
    pass

def _migrate(conn: sqlite3.Connection) -> None:
    session_cols = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "prolific_pid" not in session_cols:
        conn.execute(
            "ALTER TABLE sessions ADD COLUMN prolific_pid TEXT NOT NULL DEFAULT ''"
        )

    cols = {row["name"] for row in conn.execute("PRAGMA table_info(feedback)")}
    if "likert_8" not in cols:
        conn.execute(
            "ALTER TABLE feedback ADD COLUMN likert_8 INTEGER "
            "CHECK (likert_8 IS NULL OR likert_8 BETWEEN 1 AND 5)"
        )
    if "open_4" not in cols:
        conn.execute("ALTER TABLE feedback ADD COLUMN open_4 TEXT NOT NULL DEFAULT ''")
    if "open_5" not in cols:
        conn.execute("ALTER TABLE feedback ADD COLUMN open_5 TEXT NOT NULL DEFAULT ''")

def init(path: str | None = None) -> None:
    global _conn
    with _lock:
        if _conn is not None:
            return
        db_path = path or DB_PATH
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(_SCHEMA)
        _migrate(conn)
        conn.commit()
        _conn = conn

def reset_for_tests() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None

def _db() -> sqlite3.Connection:
    if _conn is None:
        init()
    assert _conn is not None
    return _conn

_KEY_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"

def generate_key() -> str:
    chars = [secrets.choice(_KEY_ALPHABET) for _ in range(9)]
    return f"mtm-{''.join(chars[0:3])}-{''.join(chars[3:6])}-{''.join(chars[6:9])}"

def participant_exists(key: str) -> bool:
    with _lock:
        row = _db().execute(
            "SELECT 1 FROM participants WHERE key = ? AND revoked_at IS NULL", (key,)
        ).fetchone()
    return row is not None

def insert_participant(key: str, label: str = "") -> None:
    with _lock:
        _db().execute(
            "INSERT INTO participants (key, label) VALUES (?, ?)", (key, label)
        )
        _db().commit()

def mint_participants(count: int, label: str = "") -> list[str]:
    keys: list[str] = []
    with _lock:
        while len(keys) < count:
            key = generate_key()
            try:
                _db().execute(
                    "INSERT INTO participants (key, label) VALUES (?, ?)", (key, label)
                )
            except sqlite3.IntegrityError:
                continue
            keys.append(key)
        _db().commit()
    return keys

def set_participant_revoked(key: str, revoked: bool) -> bool:
    with _lock:
        cur = _db().execute(
            "UPDATE participants SET revoked_at ="
            " CASE WHEN ? THEN datetime('now') ELSE NULL END WHERE key = ?",
            (1 if revoked else 0, key),
        )
        _db().commit()
    return cur.rowcount > 0

def list_participants() -> list[dict[str, Any]]:
    with _lock:
        rows = _db().execute(
            "SELECT p.key, p.label, p.created_at, p.revoked_at,"
            " (SELECT COUNT(*) FROM sessions s WHERE s.participant_key = p.key) AS session_count,"
            " (SELECT COUNT(*) FROM feedback f WHERE f.participant_key = p.key) AS feedback_count,"
            " (SELECT MAX(s.created_at) FROM sessions s WHERE s.participant_key = p.key) AS last_session_at"
            " FROM participants p ORDER BY p.created_at DESC, p.key"
        ).fetchall()
    return [dict(row) for row in rows]

def insert_session(session: Session) -> None:
    with _lock:
        _db().execute(
            "INSERT INTO sessions (id, participant_key, speed, description,"
            " feature_title, stakeholders, reflections, prolific_pid)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session.id,
                session.participant_key,
                session.speed,
                session.description,
                session.feature_title,
                json.dumps(session.stakeholders),
                json.dumps([r.model_dump() for r in session.reflections]),
                session.prolific_pid,
            ),
        )
        _db().commit()

def insert_chat_message(session_id: str, role: str, content: str) -> None:
    with _lock:
        _db().execute(
            "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        _db().commit()

def load_session(session_id: str) -> Session | None:
    from backend.sessions import Session as SessionDC

    with _lock:
        row = _db().execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        chat_rows = _db().execute(
            "SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return SessionDC(
        id=row["id"],
        description=row["description"],
        reflections=_reflections_adapter.validate_json(row["reflections"]),
        feature_title=row["feature_title"],
        stakeholders=json.loads(row["stakeholders"]),
        chat=[ChatMessage(role=r["role"], content=r["content"]) for r in chat_rows],
        participant_key=row["participant_key"],
        speed=row["speed"],
        prolific_pid=row["prolific_pid"],
    )

def get_sessions_by_key(key: str) -> list[dict[str, Any]]:
    with _lock:
        rows = _db().execute(
            "SELECT id, speed, description, feature_title, prolific_pid, created_at"
            " FROM sessions WHERE participant_key = ?"
            " ORDER BY created_at DESC, id",
            (key,),
        ).fetchall()
    return [dict(row) for row in rows]

def insert_feedback(
    participant_key: str,
    mode: str,
    session_id_fast: str | None,
    session_id_thinking: str | None,
    likert: dict[str, int | None],
    open_answers: dict[str, str],
    demographics: dict[str, str],
    raw: dict[str, Any],
) -> int:
    with _lock:
        try:
            cur = _db().execute(
                "INSERT INTO feedback (participant_key, mode, session_id_fast,"
                " session_id_thinking, likert_1, likert_2, likert_3, likert_4,"
                " likert_5, likert_6, likert_7, likert_8, open_1, open_2, open_3,"
                " open_4, open_5, role, experience, ethics_familiarity, age, gender,"
                " raw_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    participant_key,
                    mode,
                    session_id_fast,
                    session_id_thinking,
                    *(likert.get(f"likert_{i}") for i in range(1, 9)),
                    *(open_answers.get(f"open_{i}", "") for i in range(1, 6)),
                    *(demographics.get(d, "") for d in DEMOGRAPHIC_IDS),
                    json.dumps(raw),
                ),
            )
            _db().commit()
        except sqlite3.IntegrityError as exc:
            raise DuplicateFeedbackError(str(exc)) from exc
    return int(cur.lastrowid or 0)

def get_feedback_by_key(key: str) -> list[dict[str, Any]]:
    with _lock:
        rows = _db().execute(
            "SELECT * FROM feedback WHERE participant_key = ?"
            " ORDER BY created_at DESC, id DESC",
            (key,),
        ).fetchall()
    entries: list[dict[str, Any]] = []
    for row in rows:
        try:
            raw = json.loads(row["raw_json"])
        except (json.JSONDecodeError, TypeError):
            raw = {}
        questions = raw.get("questions", {}) if isinstance(raw, dict) else {}

        description = ""
        feature_title = ""
        prolific_pid = ""
        session_id = row["session_id_fast"] or row["session_id_thinking"]
        if session_id:
            srow = _db().execute(
                "SELECT description, feature_title, prolific_pid FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if srow is not None:
                description = srow["description"]
                feature_title = srow["feature_title"]
                prolific_pid = srow["prolific_pid"]
        entries.append(
            {
                "id": row["id"],
                "mode": row["mode"],
                "session_id_fast": row["session_id_fast"],
                "session_id_thinking": row["session_id_thinking"],
                "created_at": row["created_at"],
                "description": description,
                "feature_title": feature_title,
                "prolific_pid": prolific_pid,
                "likert": {qid: row[qid] for qid in LIKERT_IDS},
                "open": {qid: row[qid] for qid in OPEN_IDS},
                "demographics": {qid: row[qid] for qid in DEMOGRAPHIC_IDS},
                "questions": questions if isinstance(questions, dict) else {},
            }
        )
    return entries

_EXPORT_QUERIES = {
    "participants.csv": "SELECT * FROM participants ORDER BY created_at",
    "sessions.csv": "SELECT * FROM sessions ORDER BY created_at",
    "chat_messages.csv": "SELECT * FROM chat_messages ORDER BY session_id, id",
    "feedback.csv": "SELECT * FROM feedback ORDER BY created_at",
}

def export_csvs() -> dict[str, str]:
    out: dict[str, str] = {}
    with _lock:
        for filename, query in _EXPORT_QUERIES.items():
            cur = _db().execute(query)
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow([d[0] for d in cur.description])
            writer.writerows(cur.fetchall())
            out[filename] = buf.getvalue()
    return out
