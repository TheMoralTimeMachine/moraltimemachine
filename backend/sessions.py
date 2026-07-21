from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from backend import db
from backend.models import ChatMessage, Reflection

@dataclass
class Session:
    id: str
    description: str
    reflections: list[Reflection]

    feature_title: str = ""

    stakeholders: dict[str, Any] = field(default_factory=dict)
    chat: list[ChatMessage] = field(default_factory=list)

    participant_key: str = ""
    speed: str = "fast"

    prolific_pid: str = ""

_store: dict[str, Session] = {}

def create(
    description: str,
    reflections: list[Reflection],
    stakeholders: dict[str, Any] | None = None,
    feature_title: str = "",
    participant_key: str = "",
    speed: str = "fast",
    prolific_pid: str = "",
) -> Session:
    session = Session(
        id=str(uuid.uuid4()),
        description=description,
        reflections=reflections,
        feature_title=feature_title,
        stakeholders=stakeholders or {},
        participant_key=participant_key,
        speed=speed,
        prolific_pid=prolific_pid,
    )
    _store[session.id] = session
    db.insert_session(session)
    return session

def get(session_id: str) -> Session | None:
    session = _store.get(session_id)
    if session is None:
        session = db.load_session(session_id)
        if session is not None:
            _store[session.id] = session
    return session

def append(session: Session, role: str, content: str) -> None:
    session.chat.append(ChatMessage(role=role, content=content))
    db.insert_chat_message(session.id, role, content)
