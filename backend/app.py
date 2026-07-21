from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import zipfile
from contextlib import asynccontextmanager
from datetime import date

import anthropic
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from backend import db, orchestrator, sessions
from backend.auth import require_admin, require_participant
from backend.config import (
    CORS_ORIGINS,
    DEMOGRAPHIC_IDS,
    DESCRIPTION_MAX,
    DESCRIPTION_MIN,
    LIKERT_IDS,
    MESSAGE_MAX,
    MESSAGE_MIN,
    MODEL,
    NULLABLE_LIKERT_IDS,
    OPEN_IDS,
)
from backend.models import (
    AdminAnswersResponse,
    AdminKeysResponse,
    AdminMintRequest,
    AdminMintResponse,
    AdminSessionsResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    FeedbackRequest,
    FeedbackResponse,
    GetSessionResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from rag.retriever import EmptyRetrievalError, QueryTooLargeError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("backend.app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Moral Time Machine backend starting (model=%s)", MODEL)
    db.init()
    if not os.getenv("ANTHROPIC_API_KEY"):
        log.warning(
            "ANTHROPIC_API_KEY is not set — reflection and chat calls will fail. "
            "Add it to .env (see .env.example)."
        )
    await orchestrator.prewarm()
    yield

app = FastAPI(title="Moral Time Machine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": message})

@app.exception_handler(HTTPException)
async def _http_exc(request: Request, exc: HTTPException) -> JSONResponse:
    return _error(exc.status_code, str(exc.detail))

@app.exception_handler(RequestValidationError)
async def _validation_exc(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error(400, "invalid request body")

@app.exception_handler(QueryTooLargeError)
async def _query_too_large(request: Request, exc: QueryTooLargeError) -> JSONResponse:
    return _error(400, str(exc))

@app.exception_handler(EmptyRetrievalError)
async def _empty_retrieval(request: Request, exc: EmptyRetrievalError) -> JSONResponse:
    log.error("retrieval returned no precedents: %s", exc)
    return _error(502, "retrieval failed to ground the analysis; safe to retry")

@app.exception_handler(orchestrator.OffTopicError)
async def _offtopic(request: Request, exc: orchestrator.OffTopicError) -> JSONResponse:

    return _error(422, str(exc))

@app.exception_handler(anthropic.APIError)
async def _claude_error(request: Request, exc: anthropic.APIError) -> JSONResponse:
    log.error("Claude API error: %s", exc)
    return _error(502, "upstream model error; safe to retry")

@app.exception_handler(Exception)
async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unexpected error")
    return _error(500, "internal server error")

@app.get("/api/auth/check")
async def auth_check(key: str = Depends(require_participant)) -> dict:
    return {"ok": True}

@app.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session(
    req: CreateSessionRequest, key: str = Depends(require_participant)
) -> CreateSessionResponse:
    description = req.description.strip()
    if len(description) < DESCRIPTION_MIN:
        raise HTTPException(400, f"description must be at least {DESCRIPTION_MIN} characters")
    if len(description) > DESCRIPTION_MAX:
        raise HTTPException(400, f"description must be at most {DESCRIPTION_MAX} characters")

    result = await orchestrator.generate_reflections(description, req.speed)
    session = sessions.create(
        description,
        result.reflections,
        result.stakeholders,
        result.feature_title,
        participant_key=key,
        speed=req.speed,
        prolific_pid=req.prolificPid,
    )
    return CreateSessionResponse(sessionId=session.id, reflections=session.reflections)

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

_SSE_HEADERS = {

    "Cache-Control": "no-cache, no-transform",

    "X-Accel-Buffering": "no",

    "X-Content-Type-Options": "nosniff",
}

@app.get("/api/debug/stream")
async def debug_stream(count: int = 4, delay: float = 1.0) -> StreamingResponse:
    count = max(1, min(count, 20))
    delay = max(0.0, min(delay, 5.0))

    async def gen():
        for i in range(count):
            if delay:
                await asyncio.sleep(delay)
            yield _sse("tick", {"i": i, "of": count})
        yield _sse("done", {"count": count})

    return StreamingResponse(gen(), media_type="text/event-stream", headers=_SSE_HEADERS)

@app.post("/api/sessions/stream")
async def create_session_stream(
    req: CreateSessionRequest, key: str = Depends(require_participant)
) -> StreamingResponse:
    description = req.description.strip()
    if len(description) < DESCRIPTION_MIN:
        raise HTTPException(400, f"description must be at least {DESCRIPTION_MIN} characters")
    if len(description) > DESCRIPTION_MAX:
        raise HTTPException(400, f"description must be at most {DESCRIPTION_MAX} characters")

    async def event_stream():
        reflections = []
        stakeholders: dict = {}
        feature_title = ""
        try:
            async for kind, payload in orchestrator.stream_reflections(description, req.speed):
                if kind == "reflection":
                    reflections.append(payload)
                    yield _sse("reflection", payload.model_dump())
                elif kind == "title":
                    feature_title = payload
                    yield _sse("title", {"featureTitle": feature_title})
                else:
                    stakeholders = payload
            session = sessions.create(
                description,
                reflections,
                stakeholders,
                feature_title,
                participant_key=key,
                speed=req.speed,
                prolific_pid=req.prolificPid,
            )
            yield _sse("done", {"sessionId": session.id, "featureTitle": feature_title})
        except orchestrator.OffTopicError as exc:
            yield _sse("rejected", {"message": str(exc)})
        except QueryTooLargeError as exc:
            yield _sse("error", {"error": str(exc)})
        except EmptyRetrievalError as exc:
            log.error("retrieval returned no precedents: %s", exc)
            yield _sse("error", {"error": "retrieval failed to ground the analysis; safe to retry"})
        except anthropic.APIError as exc:
            log.error("Claude API error: %s", exc)
            yield _sse("error", {"error": "upstream model error; safe to retry"})
        except Exception:
            log.exception("unexpected error during reflection stream")
            yield _sse("error", {"error": "internal server error"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )

def _owned_session(session_id: str, key: str) -> sessions.Session:
    session = sessions.get(session_id)
    if session is None or session.participant_key != key:
        raise HTTPException(404, "unknown session")
    return session

@app.post("/api/sessions/{session_id}/messages", response_model=SendMessageResponse)
async def send_message(
    session_id: str, req: SendMessageRequest, key: str = Depends(require_participant)
) -> SendMessageResponse:
    message = req.message.strip()
    if len(message) < MESSAGE_MIN:
        raise HTTPException(400, "message must not be empty")
    if len(message) > MESSAGE_MAX:
        raise HTTPException(400, f"message must be at most {MESSAGE_MAX} characters")

    session = _owned_session(session_id, key)

    reply = await orchestrator.chat_reply(session, message)
    sessions.append(session, "user", message)
    sessions.append(session, "assistant", reply)
    return SendMessageResponse(reply=reply, structured=None)

@app.post("/api/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: str, req: SendMessageRequest, key: str = Depends(require_participant)
) -> StreamingResponse:
    message = req.message.strip()
    if len(message) < MESSAGE_MIN:
        raise HTTPException(400, "message must not be empty")
    if len(message) > MESSAGE_MAX:
        raise HTTPException(400, f"message must be at most {MESSAGE_MAX} characters")

    session = _owned_session(session_id, key)

    async def event_stream():
        parts: list[str] = []
        try:
            async for kind, payload in orchestrator.stream_chat_reply(session, message):
                if kind == "sources":
                    yield _sse("sources", {"sources": payload})
                else:
                    parts.append(payload)
                    yield _sse("delta", {"text": payload})
            reply = "".join(parts).strip()
            sessions.append(session, "user", message)
            sessions.append(session, "assistant", reply)
            yield _sse("done", {})
        except anthropic.APIError as exc:
            log.error("Claude API error during chat stream: %s", exc)
            yield _sse("error", {"error": "upstream model error; safe to retry"})
        except Exception:
            log.exception("unexpected error during chat stream")
            yield _sse("error", {"error": "internal server error"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )

@app.get("/api/sessions/{session_id}", response_model=GetSessionResponse)
async def get_session(
    session_id: str, key: str = Depends(require_participant)
) -> GetSessionResponse:
    session = _owned_session(session_id, key)
    return GetSessionResponse(
        sessionId=session.id,
        description=session.description,
        featureTitle=session.feature_title,
        reflections=session.reflections,
        chat=session.chat,
    )

@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    req: FeedbackRequest, key: str = Depends(require_participant)
) -> FeedbackResponse:
    for qid in LIKERT_IDS:
        value = req.likert.get(qid)
        if value is None and qid in NULLABLE_LIKERT_IDS:
            continue
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise HTTPException(400, f"{qid} must be an integer between 1 and 5")

    ids = req.sessionIds
    if not ids.fast and not ids.thinking:
        raise HTTPException(400, "at least one session id is required")
    for session_id in (ids.fast, ids.thinking):
        if session_id is not None and (
            (session := sessions.get(session_id)) is None
            or session.participant_key != key
        ):
            raise HTTPException(400, "unknown session")

    try:
        db.insert_feedback(
            participant_key=key,
            mode=req.mode,
            session_id_fast=ids.fast,
            session_id_thinking=ids.thinking,
            likert=req.likert,
            open_answers={qid: req.open.get(qid, "") for qid in OPEN_IDS},
            demographics={qid: req.demographics.get(qid, "") for qid in DEMOGRAPHIC_IDS},
            raw=req.model_dump(),
        )
    except db.DuplicateFeedbackError:
        raise HTTPException(409, "feedback already submitted for this session")
    return FeedbackResponse()

@app.get("/api/admin/check", dependencies=[Depends(require_admin)])
async def admin_check() -> dict:
    return {"ok": True}

@app.get(
    "/api/admin/keys",
    response_model=AdminKeysResponse,
    dependencies=[Depends(require_admin)],
)
async def admin_list_keys() -> AdminKeysResponse:
    return AdminKeysResponse(participants=db.list_participants())

@app.post(
    "/api/admin/keys",
    response_model=AdminMintResponse,
    dependencies=[Depends(require_admin)],
)
async def admin_mint_keys(req: AdminMintRequest) -> AdminMintResponse:
    return AdminMintResponse(keys=db.mint_participants(req.count, req.label.strip()))

@app.get(
    "/api/admin/keys/{key}/feedback",
    response_model=AdminAnswersResponse,
    dependencies=[Depends(require_admin)],
)
async def admin_key_feedback(key: str) -> AdminAnswersResponse:
    return AdminAnswersResponse(feedback=db.get_feedback_by_key(key))

@app.get(
    "/api/admin/keys/{key}/sessions",
    response_model=AdminSessionsResponse,
    dependencies=[Depends(require_admin)],
)
async def admin_key_sessions(key: str) -> AdminSessionsResponse:
    return AdminSessionsResponse(sessions=db.get_sessions_by_key(key))

@app.post("/api/admin/keys/{key}/revoke", dependencies=[Depends(require_admin)])
async def admin_revoke_key(key: str) -> dict:
    if not db.set_participant_revoked(key, True):
        raise HTTPException(404, "unknown key")
    return {"ok": True}

@app.post("/api/admin/keys/{key}/restore", dependencies=[Depends(require_admin)])
async def admin_restore_key(key: str) -> dict:
    if not db.set_participant_revoked(key, False):
        raise HTTPException(404, "unknown key")
    return {"ok": True}

@app.get("/api/admin/export", dependencies=[Depends(require_admin)])
async def admin_export() -> Response:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in db.export_csvs().items():
            zf.writestr(filename, content)
    name = f"mtm-study-export-{date.today().isoformat()}.zip"
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
