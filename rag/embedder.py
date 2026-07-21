from __future__ import annotations

import logging
import os
from typing import Sequence

import tiktoken
from openai import OpenAI

log = logging.getLogger("rag.embedder")

EMBED_MODEL = "text-embedding-3-small"
EMBED_DIMS = 1536
TOKEN_SOFT_CAP = 1500
TOKEN_HARD_CAP = 8000

MAX_BATCH_INPUTS = 512
MAX_BATCH_TOKENS = 200_000

_ENCODER = tiktoken.encoding_for_model(EMBED_MODEL)

class ChunkTooLargeError(ValueError):
    pass

def _validate_tokens(chunk_ids: Sequence[str], texts: Sequence[str]) -> None:
    for cid, text in zip(chunk_ids, texts):
        n = len(_ENCODER.encode(text))
        if n > TOKEN_HARD_CAP:
            raise ChunkTooLargeError(
                f"{cid}: {n} tokens exceeds {TOKEN_HARD_CAP} hard cap"
            )
        if n > TOKEN_SOFT_CAP:
            log.warning("%s: %d tokens exceeds soft cap of %d", cid, n, TOKEN_SOFT_CAP)

def _batches(texts: Sequence[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    cur_tokens = 0
    for i, text in enumerate(texts):
        n = len(_ENCODER.encode(text))
        if i > start and (i - start >= MAX_BATCH_INPUTS or cur_tokens + n > MAX_BATCH_TOKENS):
            spans.append((start, i))
            start = i
            cur_tokens = 0
        cur_tokens += n
    spans.append((start, len(texts)))
    return spans

def embed(chunk_ids: Sequence[str], texts: Sequence[str]) -> list[list[float]]:
    if len(chunk_ids) != len(texts):
        raise ValueError("chunk_ids and texts must be the same length")
    if not texts:
        return []

    _validate_tokens(chunk_ids, texts)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set; populate .env")

    client = OpenAI(api_key=api_key)
    spans = _batches(texts)
    log.info("Embedding %d chunks via %s in %d batch(es)", len(texts), EMBED_MODEL, len(spans))
    out: list[list[float]] = []
    for start, end in spans:
        resp = client.embeddings.create(model=EMBED_MODEL, input=list(texts[start:end]))
        out.extend(d.embedding for d in resp.data)
    return out
