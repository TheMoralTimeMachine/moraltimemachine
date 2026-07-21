from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Dimension = Literal[
    "tomorrow",
    "in_five_years",
    "public_scrutiny",
    "stakeholder_impact",
]

HarmCategory = Literal[
    "Accountability",
    "Censorship",
    "Disparity",
    "Disruptive activity",
    "False information",
    "Fraudulent activity",
    "Inappropriate content",
    "Manipulation",
    "Privacy",
    "Transparency",
]

Role = Literal["user", "assistant"]

Speed = Literal["thinking", "fast"]

class HarmRef(BaseModel):

    category: HarmCategory
    explanation: str = ""

class ReflectionPoint(BaseModel):
    point: str
    title: str = ""
    context_label: str | None = None
    context: str | None = None
    context_detail: str | None = None
    harms: list[HarmRef]
    mitigation: str

class Reflection(BaseModel):
    dimension: Dimension
    title: str
    body: str
    harms: list[HarmRef]
    mitigation: str
    points: list[ReflectionPoint]

class ChatMessage(BaseModel):
    role: Role
    content: str

class ChatSource(BaseModel):

    source: str
    title: str

class CreateSessionRequest(BaseModel):
    description: str
    speed: Speed = "fast"

    prolificPid: str = ""

class CreateSessionResponse(BaseModel):
    sessionId: str
    reflections: list[Reflection]

class SendMessageRequest(BaseModel):
    message: str

class SendMessageResponse(BaseModel):
    reply: str

    structured: Any | None = None

class GetSessionResponse(BaseModel):
    sessionId: str
    description: str
    featureTitle: str = ""
    reflections: list[Reflection]
    chat: list[ChatMessage]

class FeedbackSessionIds(BaseModel):

    fast: str | None = None
    thinking: str | None = None

class FeedbackRequest(BaseModel):
    sessionIds: FeedbackSessionIds
    mode: Literal["fast", "thinking", "compare"]

    likert: dict[str, int | None]
    open: dict[str, str] = {}

    demographics: dict[str, str] = {}

    questions: dict[str, str] = {}

class FeedbackResponse(BaseModel):
    ok: bool = True

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Human-readable message the frontend can surface")

class AdminMintRequest(BaseModel):
    count: int = Field(ge=1, le=200)
    label: str = ""

class AdminMintResponse(BaseModel):
    keys: list[str]

class AdminParticipant(BaseModel):

    key: str
    label: str
    created_at: str
    revoked_at: str | None = None
    session_count: int
    feedback_count: int
    last_session_at: str | None = None

class AdminKeysResponse(BaseModel):
    participants: list[AdminParticipant]

class AdminFeedbackEntry(BaseModel):

    id: int
    mode: Literal["fast", "thinking", "compare"]
    session_id_fast: str | None = None
    session_id_thinking: str | None = None
    created_at: str
    description: str = ""
    feature_title: str = ""

    prolific_pid: str = ""
    likert: dict[str, int | None]
    open: dict[str, str]
    demographics: dict[str, str]
    questions: dict[str, str] = {}

class AdminAnswersResponse(BaseModel):
    feedback: list[AdminFeedbackEntry]

class AdminSession(BaseModel):

    id: str
    speed: str
    description: str = ""
    feature_title: str = ""
    prolific_pid: str = ""
    created_at: str

class AdminSessionsResponse(BaseModel):
    sessions: list[AdminSession]
