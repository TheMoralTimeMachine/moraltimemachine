from __future__ import annotations

import logging
import sys
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Literal

import chromadb
import tiktoken
from chromadb.config import Settings
from dotenv import load_dotenv

from rag.embedder import embed
from rag.schema import RetrievedChunk, SPECTRUM_LABELS

load_dotenv()

log = logging.getLogger("rag.retriever")

logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

REPO_ROOT = Path(__file__).resolve().parent.parent
CHROMA_PATH = REPO_ROOT / "chroma_db"
COLLECTION_NAME = "precedents"

OVERFETCH = 100
DEFAULT_PER_SOURCE_MAX = 2
RELAX_SEQUENCE = (2, 3, 4)
QUERY_TOKEN_LIMIT = 1000

_RERANKER_MODEL = "BAAI/bge-reranker-base"

ScoringMethod = Literal["cosine", "cross-encoder"]
DEFAULT_SCORING: ScoringMethod = "cosine"

_QUERY_ENC = tiktoken.get_encoding("cl100k_base")

class EmptyRetrievalError(RuntimeError):
    pass

class QueryTooLargeError(ValueError):

    def __init__(self, token_count: int, limit: int):
        self.token_count = token_count
        self.limit = limit
        super().__init__(f"Query has {token_count} tokens, exceeds limit of {limit}")

_collection = None
_reranker = None

def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = client.get_collection(name=COLLECTION_NAME)
    return _collection

def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        print(f"loading reranker {_RERANKER_MODEL}...", file=sys.stderr)
        _reranker = CrossEncoder(_RERANKER_MODEL, max_length=512)
    return _reranker

@lru_cache(maxsize=128)
def _embed_query(query: str) -> tuple[float, ...]:
    [vec] = embed(["query"], [query])
    return tuple(vec)

def _label_field(label: str) -> str:
    return f"harm_label_{label.lower().replace(' ', '_')}"

def _build_where(
    chunk_types: list[str] | None,
    harm_labels: list[str] | None,
) -> dict | None:
    clauses: list[dict] = []
    if chunk_types:
        clauses.append({"chunk_type": {"$in": list(chunk_types)}})
    if harm_labels:
        for lab in harm_labels:
            if lab not in SPECTRUM_LABELS:
                raise ValueError(f"Unknown harm label {lab!r}")
        if len(harm_labels) == 1:
            clauses.append({_label_field(harm_labels[0]): True})
        else:
            clauses.append({"$or": [{_label_field(l): True} for l in harm_labels]})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}

def _chunk_from_row(cid: str, md: dict, doc: str, similarity: float) -> RetrievedChunk:
    labels = [l for l in SPECTRUM_LABELS if md.get(_label_field(l))]
    return RetrievedChunk(
        chunk_id=cid,
        source=md["source"],
        source_full_title=md["source_full_title"],
        chunk_type=md["chunk_type"],
        harm_labels=sorted(labels),
        body=doc,
        similarity=similarity,
    )

def _score_cosine(
    query: str,
    where: dict | None,
) -> list[RetrievedChunk]:
    qvec = _embed_query(query)
    col = _get_collection()
    res = col.query(
        query_embeddings=[list(qvec)],
        n_results=OVERFETCH,
        where=where,
    )
    ids = res["ids"][0]
    distances = res["distances"][0]
    metadatas = res["metadatas"][0]
    documents = res["documents"][0]
    return [
        _chunk_from_row(cid, md, doc, similarity=1.0 - float(dist))
        for cid, dist, md, doc in zip(ids, distances, metadatas, documents)
    ]

def _score_cross_encoder(
    query: str,
    where: dict | None,
) -> list[RetrievedChunk]:
    col = _get_collection()
    res = col.get(where=where, include=["documents", "metadatas"])
    ids = res["ids"]
    metadatas = res["metadatas"]
    documents = res["documents"]
    if not ids:
        return []
    candidates = [
        _chunk_from_row(cid, md, doc, similarity=0.0)
        for cid, md, doc in zip(ids, metadatas, documents)
    ]
    pairs = [(query, c.body) for c in candidates]
    scores = _get_reranker().predict(pairs).tolist()
    scored = [replace(c, similarity=float(s)) for c, s in zip(candidates, scores)]
    scored.sort(key=lambda c: c.similarity, reverse=True)
    return scored

def _dedup_split_siblings(candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
    if not candidates:
        return []
    seen_parents: set[str] = set()
    kept: list[RetrievedChunk] = []
    col = _get_collection()
    parent_lookup = col.get(ids=[c.chunk_id for c in candidates], include=["metadatas"])
    parent_by_id = {
        cid: (md.get("part_of") or "")
        for cid, md in zip(parent_lookup["ids"], parent_lookup["metadatas"])
    }
    for c in candidates:
        parent = parent_by_id.get(c.chunk_id, "")
        if parent:
            if parent in seen_parents:
                log.info("dropping split sibling %s (parent %s already represented)", c.chunk_id, parent)
                continue
            seen_parents.add(parent)
        kept.append(c)
    return kept

def _apply_diversity_cap(
    candidates: list[RetrievedChunk],
    k: int,
    per_source_max: int,
) -> list[RetrievedChunk]:
    counts: dict[str, int] = {}
    out: list[RetrievedChunk] = []
    for c in candidates:
        if counts.get(c.source, 0) >= per_source_max:
            continue
        out.append(c)
        counts[c.source] = counts.get(c.source, 0) + 1
        if len(out) >= k:
            break
    return out

def retrieve(
    query: str,
    k: int = 5,
    chunk_types: list[str] | None = None,
    harm_labels: list[str] | None = None,
    scoring_method: ScoringMethod = DEFAULT_SCORING,
) -> list[RetrievedChunk]:
    n_tokens = len(_QUERY_ENC.encode(query))
    if n_tokens > QUERY_TOKEN_LIMIT:
        raise QueryTooLargeError(n_tokens, QUERY_TOKEN_LIMIT)

    log.info("retrieve: q=%r k=%d chunk_types=%s scoring=%s",
             query[:200], k, chunk_types, scoring_method)

    where = _build_where(chunk_types, harm_labels)

    if scoring_method == "cosine":
        candidates = _score_cosine(query, where)
    elif scoring_method == "cross-encoder":
        candidates = _score_cross_encoder(query, where)
    else:
        raise ValueError(f"Unknown scoring_method {scoring_method!r}")

    if not candidates:
        raise EmptyRetrievalError(f"No chunks matched filters for query {query[:80]!r}")

    candidates = _dedup_split_siblings(candidates)

    selected: list[RetrievedChunk] = []
    relaxed_at: int | None = None
    for cap in RELAX_SEQUENCE:
        selected = _apply_diversity_cap(candidates, k, cap)
        if len(selected) >= k:
            if cap > DEFAULT_PER_SOURCE_MAX:
                log.warning(
                    "per-source cap relaxed to %d to reach k=%d for query %r",
                    cap, k, query[:80],
                )
                relaxed_at = cap
            break
        relaxed_at = cap
    else:
        log.warning(
            "under-fill: only %d/%d chunks after relaxing to cap=%d for query %r",
            len(selected), k, RELAX_SEQUENCE[-1], query[:80],
        )

    if not selected:
        raise EmptyRetrievalError(f"No chunks survived diversity filters for query {query[:80]!r}")

    log.info(
        "retrieve: returning %d chunks; sources=%s; scores=%s",
        len(selected),
        [c.source for c in selected],
        [round(c.similarity, 3) for c in selected],
    )
    return selected
