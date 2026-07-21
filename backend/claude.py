from __future__ import annotations

import json
from functools import lru_cache

import anthropic

import logging

from backend.config import CHAT_EFFORT, CHAT_MODEL, GATE_MODEL, MODEL
from backend.models import ChatMessage

log = logging.getLogger("backend.claude")

_REFLECTION_MAX_TOKENS = 16000
_CHAT_MAX_TOKENS = 4000

_GATE_MAX_TOKENS = 256

_STAKEHOLDER_MAX_TOKENS = 2048

@lru_cache(maxsize=1)
def _client() -> anthropic.AsyncAnthropic:

    return anthropic.AsyncAnthropic()

def _text_block(content) -> str:
    for block in content:
        if block.type == "text":
            return block.text
    raise ValueError("Claude response contained no text block")

async def complete_structured(
    frozen_system: str,
    volatile_system: str,
    user: str,
    schema: dict,
    effort: str,
) -> tuple[dict, anthropic.types.Usage]:
    async with _client().messages.stream(
        model=MODEL,
        max_tokens=_REFLECTION_MAX_TOKENS,
        thinking={"type": "adaptive"},
        output_config={
            "format": {"type": "json_schema", "schema": schema},
            "effort": effort,
        },
        system=[
            {"type": "text", "text": frozen_system},
            {"type": "text", "text": volatile_system},
        ],
        messages=[{"role": "user", "content": user}],
    ) as stream:
        message = await stream.get_final_message()
    return json.loads(_text_block(message.content)), message.usage

async def complete_structured_fast(
    frozen_system: str,
    volatile_system: str,
    user: str,
    schema: dict,
    model: str,
    max_tokens: int = _STAKEHOLDER_MAX_TOKENS,
) -> tuple[dict, anthropic.types.Usage]:
    resp = await _client().messages.create(
        model=model,
        max_tokens=max_tokens,
        output_config={"format": {"type": "json_schema", "schema": schema}},
        system=[
            {"type": "text", "text": frozen_system},
            {"type": "text", "text": volatile_system},
        ],
        messages=[{"role": "user", "content": user}],
    )
    return json.loads(_text_block(resp.content)), resp.usage

async def classify(system: str, user: str, schema: dict) -> dict:
    resp = await _client().messages.create(
        model=GATE_MODEL,
        max_tokens=_GATE_MAX_TOKENS,

        output_config={"format": {"type": "json_schema", "schema": schema}},
        system=[{"type": "text", "text": system}],
        messages=[{"role": "user", "content": user}],
    )
    return json.loads(_text_block(resp.content))

async def complete_chat(system: str, history: list[ChatMessage], message: str) -> str:
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": message})
    resp = await _client().messages.create(
        model=MODEL,
        max_tokens=_CHAT_MAX_TOKENS,
        output_config={"effort": "medium"},
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )
    return _text_block(resp.content).strip()

async def stream_chat(system: str, history: list[ChatMessage], message: str):
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": message})
    async with _client().messages.stream(
        model=CHAT_MODEL,
        max_tokens=_CHAT_MAX_TOKENS,
        output_config={"effort": CHAT_EFFORT},
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text
        final = await stream.get_final_message()

    u = final.usage
    log.info(
        "chat tokens: in=%s out=%s cache_read=%s cache_write=%s",
        getattr(u, "input_tokens", 0),
        getattr(u, "output_tokens", 0),
        getattr(u, "cache_read_input_tokens", 0) or 0,
        getattr(u, "cache_creation_input_tokens", 0) or 0,
    )
