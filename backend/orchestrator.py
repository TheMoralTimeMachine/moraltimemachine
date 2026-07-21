from __future__ import annotations

import asyncio
import logging
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

from backend import claude, config, prompts
from backend.config import (
    CHAT_HISTORY_MAX_MESSAGES,
    CHAT_RETRIEVAL_K,
    DIMENSION_ORDER,
    FRONTEND_HARMS,
    GATE_SCHEMA,
    GENERIC_CONTEXT_CHUNK_TYPES,
    GENERIC_CONTEXT_QUERY_AUGMENT,
    GENERIC_CONTEXT_SCHEMA,
    OFFTOPIC_MESSAGE,
    REFLECTION_EFFORT,
    RETRIEVAL_BY_DIMENSION,
    RETRIEVAL_K,
    STAKEHOLDER_CHUNK_TYPES,
    STAKEHOLDER_MODEL,
    STAKEHOLDER_QUERY_AUGMENT,
    STAKEHOLDER_SCHEMA,
)
from backend.models import ChatMessage, HarmRef, Reflection, ReflectionPoint
from backend.sessions import Session
from rag.retriever import EmptyRetrievalError, QueryTooLargeError, retrieve

log = logging.getLogger("backend.orchestrator")

_FRONTEND_HARMS = set(FRONTEND_HARMS)

_WORD_RE = re.compile(r"[A-Za-z]{3,}")

class OffTopicError(Exception):
    pass

@dataclass
class PipelineOutput:

    reflections: list[Reflection]
    stakeholders: dict
    feature_title: str

def _clean_harms(raw: list[dict]) -> list[HarmRef]:
    seen: set[str] = set()
    out: list[HarmRef] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cat = (item.get("category") or "").strip()
        if cat in _FRONTEND_HARMS and cat not in seen:
            seen.add(cat)
            out.append(HarmRef(category=cat, explanation=(item.get("explanation") or "").strip()))
    return out

@asynccontextmanager
async def _timed(label: str, sink: list[tuple[str, float]]):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        sink.append((label, elapsed))
        log.info("timing: %-28s %6.2fs", label, elapsed)

def _u(usage, field: str) -> int:
    return getattr(usage, field, 0) or 0

async def _retrieve(
    query: str,
    chunk_types: tuple[str, ...] | None,
    scoring_method: str | None = None,
    k: int = RETRIEVAL_K,
):
    kwargs = {"scoring_method": scoring_method} if scoring_method else {}
    chunks = await asyncio.to_thread(
        retrieve, query, k, list(chunk_types) if chunk_types else None, **kwargs
    )
    return chunks

async def _gate(description: str) -> None:
    if not _WORD_RE.search(description):
        log.info("gate: rejected (no alphabetic word) %r", description[:80])
        raise OffTopicError(OFFTOPIC_MESSAGE)
    result = await claude.classify(
        prompts.gate_system_text(), prompts.gate_user_text(description), GATE_SCHEMA
    )
    if not result.get("is_software_feature"):
        log.info("gate: rejected — %s | %r", result.get("reason", ""), description[:80])
        raise OffTopicError(OFFTOPIC_MESSAGE)

async def _stakeholders(
    description: str,
    timings: list[tuple[str, float]],
    tokens: list[tuple[str, object]],
) -> dict:
    async with _timed("stakeholders.retrieve", timings):
        chunks = await _retrieve(
            description + STAKEHOLDER_QUERY_AUGMENT, STAKEHOLDER_CHUNK_TYPES, scoring_method="cosine"
        )
    log.info("stakeholders retrieved %d chunks: %s", len(chunks), [c.chunk_id for c in chunks])
    async with _timed("stakeholders.claude", timings):
        data, usage = await claude.complete_structured_fast(
            prompts.frozen_system_text(),
            prompts.stakeholder_volatile_text(prompts.render_precedents(chunks)),
            prompts.stakeholder_user_text(description),
            STAKEHOLDER_SCHEMA,
            STAKEHOLDER_MODEL,
        )
    tokens.append(("stakeholders", usage))
    return data

async def _generic_context(
    description: str,
    timings: list[tuple[str, float]],
    tokens: list[tuple[str, object]],
) -> dict:
    async with _timed("generic_context.retrieve", timings):
        chunks = await _retrieve(
            description + GENERIC_CONTEXT_QUERY_AUGMENT,
            GENERIC_CONTEXT_CHUNK_TYPES,
            scoring_method="cosine",
        )
    log.info("generic_context retrieved %d chunks: %s", len(chunks), [c.chunk_id for c in chunks])
    async with _timed("generic_context.claude", timings):
        data, usage = await claude.complete_structured_fast(
            prompts.frozen_system_text(),
            prompts.generic_context_volatile_text(prompts.render_precedents(chunks)),
            prompts.generic_context_user_text(description),
            GENERIC_CONTEXT_SCHEMA,
            STAKEHOLDER_MODEL,
        )
    tokens.append(("generic_context", usage))
    return data

def _normalize_points(dimension: str, raw: dict) -> list[ReflectionPoint]:
    out: list[ReflectionPoint] = []
    if dimension in ("tomorrow", "in_five_years"):
        for it in raw.get("harms", []):
            affected = ", ".join(it.get("affected_stakeholders", [])).strip()
            out.append(
                ReflectionPoint(
                    point=it["harm"].strip(),
                    title=it.get("title", "").strip(),
                    context_label="Affects" if affected else None,
                    context=affected or None,
                    harms=_clean_harms(it.get("harm_categories", [])),
                    mitigation=it.get("mitigation", "").strip(),
                )
            )
    elif dimension == "public_scrutiny":
        for it in raw.get("concerns", []):
            who = it.get("who_raises_it", "").strip()
            framing = it.get("framing", "").strip()
            out.append(
                ReflectionPoint(
                    point=it["concern"].strip(),
                    title=it.get("title", "").strip(),
                    context_label="Raised by" if who else None,
                    context=who or None,
                    context_detail=framing or None,
                    harms=_clean_harms(it.get("harm_categories", [])),
                    mitigation=it.get("mitigation", "").strip(),
                )
            )
    elif dimension == "stakeholder_impact":
        for it in raw.get("stakeholder_impacts", []):
            who = (it.get("stakeholder") or "").strip()
            out.append(
                ReflectionPoint(
                    point=it["impact"].strip(),
                    context_label="Stakeholder" if who else None,
                    context=who or None,
                    harms=_clean_harms(it.get("harm_categories", [])),
                    mitigation=it.get("mitigation", "").strip(),
                )
            )
    return out

def _to_reflection(dimension: str, raw: dict) -> Reflection:
    summary = raw["summary"]
    return Reflection(
        dimension=dimension,
        title=summary["title"].strip(),
        body=summary["description"].strip(),
        harms=_clean_harms(summary.get("key_harm_categories", [])),
        mitigation=summary["key_mitigation"].strip(),
        points=_normalize_points(dimension, raw),
    )

async def _reflect(
    dim: str,
    description: str,
    stakeholders: dict,
    prior: list[tuple[str, dict]],
    timings: list[tuple[str, float]],
    tokens: list[tuple[str, object]],
    speed: str = "fast",
) -> tuple[Reflection, dict]:
    cfg = RETRIEVAL_BY_DIMENSION[dim]
    query = f"{description}{cfg.query_augment}"
    async with _timed(f"{dim}.retrieve", timings):
        chunks = await _retrieve(query, cfg.chunk_types, scoring_method="cosine")
    log.info(
        "dimension=%s retrieved %d chunks: %s",
        dim, len(chunks), [c.chunk_id for c in chunks],
    )
    async with _timed(f"{dim}.claude", timings):
        raw, usage = await claude.complete_structured(
            prompts.frozen_system_text(),
            prompts.reflection_volatile_text(cfg, prompts.render_precedents(chunks)),
            prompts.reflection_user_text(cfg, description, stakeholders, prior, speed),
            config.response_schema(cfg),
            REFLECTION_EFFORT,
        )
    tokens.append((dim, usage))
    return _to_reflection(dim, raw), raw

async def _reflect_parallel(
    dims: list[str],
    description: str,
    stakeholders: dict,
    prior: list[tuple[str, dict]],
    timings: list[tuple[str, float]],
    tokens: list[tuple[str, object]],
    speed: str = "fast",
):
    tasks = [
        asyncio.create_task(_reflect(dim, description, stakeholders, prior, timings, tokens, speed))
        for dim in dims
    ]
    try:
        for fut in asyncio.as_completed(tasks):
            reflection, _raw = await fut
            yield "reflection", reflection
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()

async def stream_reflections(description: str, speed: str = "fast"):
    await _gate(description)

    timings: list[tuple[str, float]] = []
    tokens: list[tuple[str, object]] = []
    total_start = time.perf_counter()

    if speed == "fast":
        stakeholders = await _generic_context(description, timings, tokens)
    else:
        stakeholders = await _stakeholders(description, timings, tokens)

    feature_title = str(stakeholders.pop("feature_title", "")).strip()
    yield "title", feature_title

    if speed == "thinking":
        prior: list[tuple[str, dict]] = []
        for dim in DIMENSION_ORDER:
            reflection, raw = await _reflect(
                dim, description, stakeholders, prior, timings, tokens, speed
            )
            prior.append((RETRIEVAL_BY_DIMENSION[dim].label, raw))
            yield "reflection", reflection
    else:
        async for ev in _reflect_parallel(
            DIMENSION_ORDER, description, stakeholders, [], timings, tokens, speed
        ):
            yield ev

    total = time.perf_counter() - total_start
    retrieve_total = sum(s for label, s in timings if label.endswith(".retrieve"))
    claude_total = sum(s for label, s in timings if label.endswith(".claude"))
    log.info(
        "timing: TOTAL %.2fs (retrieve=%.2fs claude=%.2fs) | %s",
        total, retrieve_total, claude_total,
        " ".join(f"{label}={s:.1f}" for label, s in timings),
    )
    in_total = sum(_u(u, "input_tokens") for _, u in tokens)
    out_total = sum(_u(u, "output_tokens") for _, u in tokens)
    cache_read = sum(_u(u, "cache_read_input_tokens") for _, u in tokens)
    cache_write = sum(_u(u, "cache_creation_input_tokens") for _, u in tokens)
    log.info(
        "tokens: TOTAL in=%d out=%d (cache_read=%d cache_write=%d) | %s",
        in_total, out_total, cache_read, cache_write,
        " ".join(
            f"{label}=in{_u(u, 'input_tokens')}/out{_u(u, 'output_tokens')}"
            f"/cr{_u(u, 'cache_read_input_tokens')}/cw{_u(u, 'cache_creation_input_tokens')}"
            for label, u in tokens
        ),
    )

    yield "done", stakeholders

async def generate_reflections(
    description: str, speed: str = "fast"
) -> PipelineOutput:
    reflections: list[Reflection] = []
    stakeholders: dict = {}
    feature_title = ""
    async for kind, payload in stream_reflections(description, speed):
        if kind == "reflection":
            reflections.append(payload)
        elif kind == "title":
            feature_title = payload
        else:
            stakeholders = payload
    reflections.sort(key=lambda r: DIMENSION_ORDER.index(r.dimension))
    return PipelineOutput(
        reflections=reflections, stakeholders=stakeholders, feature_title=feature_title
    )

async def chat_reply(session: Session, message: str) -> str:
    return await claude.complete_chat(
        prompts.chat_system_text(session),
        list(session.chat),
        message,
    )

def _dedup_sources(chunks) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for c in chunks:
        if c.source in seen:
            continue
        seen.add(c.source)
        out.append({"source": c.source, "title": c.source_full_title})
    return out

async def stream_chat_reply(session: Session, message: str):
    try:
        chunks = await _retrieve(
            message, None, scoring_method="cosine", k=CHAT_RETRIEVAL_K
        )
    except (EmptyRetrievalError, QueryTooLargeError) as exc:
        log.info("chat retrieval skipped: %s", exc)
        chunks = []
    log.info("chat retrieved %d chunks: %s", len(chunks), [c.chunk_id for c in chunks])

    yield "sources", _dedup_sources(chunks)

    system = prompts.chat_system_text(session)
    history = list(session.chat)[-CHAT_HISTORY_MAX_MESSAGES:]
    user = prompts.chat_user_text(message, chunks)
    async for delta in claude.stream_chat(system, history, user):
        yield "delta", delta

async def prewarm() -> None:
    try:
        await asyncio.to_thread(retrieve, "warmup", 1, None, scoring_method="cosine")
        log.info("retriever prewarm complete")
    except Exception as exc:
        log.warning("retriever prewarm skipped: %s", exc)

__all__ = [
    "generate_reflections",
    "stream_reflections",
    "chat_reply",
    "stream_chat_reply",
    "prewarm",
    "PipelineOutput",
    "OffTopicError",
    "ChatMessage",
]
