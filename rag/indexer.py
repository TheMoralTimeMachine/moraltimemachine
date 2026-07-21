from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

from rag.embedder import EMBED_DIMS, embed
from rag.schema import SPECTRUM_LABELS

log = logging.getLogger("rag.indexer")

REPO_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_FILE = REPO_ROOT / "rag" / "chunks.json"
CHROMA_PATH = REPO_ROOT / "chroma_db"
COLLECTION_NAME = "precedents"

def _label_field(label: str) -> str:
    return f"harm_label_{label.lower().replace(' ', '_')}"

def _build_metadata(chunk: dict) -> dict:
    chunk_labels = set(chunk.get("harm_labels") or [])
    md: dict = {
        "chunk_id": chunk["chunk_id"],
        "source": chunk["source"],
        "source_full_title": chunk["source_full_title"],
        "chunk_type": chunk["chunk_type"],
        "original_label": chunk["original_label"],
        "harm_labels_display": ", ".join(sorted(chunk_labels)),
        "stakeholders_display": ", ".join(chunk.get("stakeholders") or []),
        "part_of": chunk.get("part_of") or "",
    }
    for label in SPECTRUM_LABELS:
        md[_label_field(label)] = label in chunk_labels
    return md

def _load_chunks() -> list[dict]:
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(f"chunks.json not found at {CHUNKS_FILE} — run rag.chunker first")
    with CHUNKS_FILE.open() as f:
        chunks = json.load(f)
    log.info("Loaded %d chunks from %s", len(chunks), CHUNKS_FILE.name)
    return chunks

def index() -> int:
    t0 = time.perf_counter()
    chunks = _load_chunks()

    chunk_ids = [c["chunk_id"] for c in chunks]
    bodies = [c["body"] for c in chunks]
    embeddings = embed(chunk_ids, bodies)

    if any(len(e) != EMBED_DIMS for e in embeddings):
        raise RuntimeError(f"Expected {EMBED_DIMS}-dim embeddings; got mixed sizes")

    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        client.delete_collection(name=COLLECTION_NAME)
        log.info("Deleted existing collection %r", COLLECTION_NAME)
    except Exception as e:
        log.debug("No existing collection to delete (%s)", e)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    metadatas = [_build_metadata(c) for c in chunks]
    collection.add(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=bodies,
        metadatas=metadatas,
    )

    elapsed = time.perf_counter() - t0
    n = collection.count()
    log.info("Indexed %d chunks in %.1fs", n, elapsed)
    print(f"Indexed {n} chunks in {elapsed:.1f}s")
    return n

def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    load_dotenv()
    index()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
