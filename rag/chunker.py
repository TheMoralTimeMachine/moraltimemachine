from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Iterable

import tiktoken

from rag.aiaaic import build_aiaaic_chunks
from rag.schema import (
    CHUNK_TYPES,
    SPECTRUM_LABELS,
    Chunk,
    UnmappedLabelError,
)

log = logging.getLogger("rag.chunker")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

REPO_RAG_ROOT = Path(__file__).resolve().parent
PAPERS_ROOT = REPO_RAG_ROOT / "papers"
CLEANED_ROOT = PAPERS_ROOT / "cleaned"
MAPPING_TABLE = PAPERS_ROOT / "mapping-table.md"
OVERRIDES_FILE = PAPERS_ROOT / "manual-overrides.json"
OUTPUT_FILE = REPO_RAG_ROOT / "chunks.json"

TOKEN_FLOOR = 100
TOKEN_SOFT_CAP = 800
TOKEN_HARD_CAP = 1500

ENCODER = tiktoken.get_encoding("cl100k_base")

SOURCES: dict[str, dict] = {
    "crossing-margins": {
        "path": "crossing-margins.md",
        "title": "Crossing Margins: Intersectional Users' Ethical Concerns about Software (Olson et al., 2024)",
        "chunk_type": "qualitative-finding",
    },
    "along-the-margins": {
        "path": "along-the-margins.md",
        "title": "Along the Margins: Marginalized Communities' Ethical Concerns about Social Platforms (Olson, Guzman & Kunneman, 2023)",
        "chunk_type": "qualitative-finding",
    },
    "the-best-ends-by-the-best-means": {
        "path": "the-best-ends-by-the-best-means.md",
        "title": "The Best Ends by the Best Means: Ethical Concerns in App Reviews (Tjikhoeri, Olson & Guzman, 2024)",
        "chunk_type": "qualitative-finding",
    },
    "harm-cases": {
        "path": "harm-cases.md",
        "title": "Harm Identified in Past Technologies",
        "chunk_type": "real-incident",
    },
}

STOPWORDS = frozenset({"a", "an", "the", "of", "and", "or", "to", "in", "for", "on", "with"})

CONTEXT_DEPENDENT = object()

def slugify(text: str, *, max_len: int = 30) -> str:
    norm = unicodedata.normalize("NFKD", text)
    ascii_only = norm.encode("ascii", "ignore").decode("ascii").lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    if not cleaned:
        return ""
    parts = [p for p in cleaned.split("-") if p and p not in STOPWORDS]
    if not parts:
        parts = cleaned.split("-")
    slug = "-".join(parts)
    if len(slug) <= max_len:
        return slug
    truncated = slug[:max_len]
    last_hyphen = truncated.rfind("-")
    return truncated[:last_hyphen] if last_hyphen > 0 else truncated

def count_tokens(text: str) -> int:
    return len(ENCODER.encode(text))

_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_TABLE_ROW_RE = re.compile(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", re.MULTILINE)

def load_mapping(path: Path = MAPPING_TABLE) -> dict[str, object]:
    text = path.read_text()
    mapping: dict[str, object] = {}
    for col1, _col2, col3 in _TABLE_ROW_RE.findall(text):
        if col1 in {"Source Label", ""} or set(col1) <= {"-"}:
            continue
        original = col1.strip()
        rhs = col3.strip()
        if "no equivalent" in rhs.lower():
            mapping[original.lower()] = []
            continue
        if "context-dependent" in rhs.lower() or " or " in rhs.lower():
            mapping[original.lower()] = CONTEXT_DEPENDENT
            continue
        bolded = _BOLD_RE.findall(rhs)
        if not bolded:
            continue
        labels = [b.strip() for b in bolded]
        if "+" in rhs:
            mapping[original.lower()] = labels
        else:
            mapping[original.lower()] = labels[:1]
    return mapping

def load_overrides(path: Path = OVERRIDES_FILE) -> dict[str, list[str]]:
    raw = json.loads(path.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_")}

def harmonize(
    *,
    original_label: str,
    source: str,
    mapping: dict[str, object],
    overrides: dict[str, list[str]],
) -> list[str]:
    key = f"{source}__{slugify(original_label)}"
    if key in overrides:
        labels = overrides[key]
    else:
        entry = mapping.get(original_label.lower())
        if entry is None:
            raise UnmappedLabelError(
                f"Label {original_label!r} (source={source!r}) not in mapping-table.md"
            )
        if entry is CONTEXT_DEPENDENT:
            raise UnmappedLabelError(
                f"Label {original_label!r} (source={source!r}) is context-dependent; "
                f"add override for key {key!r} in manual-overrides.json"
            )
        labels = list(entry)
    if not labels:
        return []
    bad = [lbl for lbl in labels if lbl not in SPECTRUM_LABELS]
    if bad:
        raise UnmappedLabelError(
            f"Harmonized label(s) {bad!r} for {original_label!r} not in SPECTRUM_LABELS"
        )
    return sorted(set(labels))

_H2_SPLIT_RE = re.compile(r"^## ", re.MULTILINE)

def split_h2_sections(text: str) -> list[tuple[str, str]]:
    parts = _H2_SPLIT_RE.split(text)
    sections: list[tuple[str, str]] = []
    for part in parts[1:]:
        head, _, body = part.partition("\n")
        sections.append((head.strip(), body.strip()))
    return sections

_HARM_CASE_HEADING_RE = re.compile(r"^(.*?)\s*\(chunk_id:\s*(\S+)\)\s*$")
_HARM_CASE_LABEL_LINE_RE = re.compile(r"^\s*-\s*([A-Z][A-Za-z ]+?):", re.MULTILINE)
_HARM_CASE_LABEL_BLOCK_RE = re.compile(
    r"^Categorized harms:\s*\n((?:\s*-\s*.*(?:\n|$))+)", re.MULTILINE
)

def _qualitative_body(*, original_label: str, source: str, body: str) -> str:
    return f"[{original_label} — {source}]\n\n{body}"

def _incident_body(*, original_label: str, body: str) -> str:
    return f"[Real incident: {original_label}]\n\n{body}"

def chunk_qualitative(
    *,
    source: str,
    spec: dict,
    text: str,
    mapping: dict[str, object],
    overrides: dict[str, list[str]],
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for heading, body in split_h2_sections(text):
        original_label = heading.strip()
        harm_labels = harmonize(
            original_label=original_label,
            source=source,
            mapping=mapping,
            overrides=overrides,
        )
        if not harm_labels:
            log.warning("dropping section %s::%s (no Spectrum equivalent)", source, original_label)
            continue
        chunk_id = f"{source}__{slugify(original_label)}"
        full_body = _qualitative_body(
            original_label=original_label,
            source=source,
            body=body,
        )
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                source=source,
                source_full_title=spec["title"],
                chunk_type=spec["chunk_type"],
                original_label=original_label,
                harm_labels=harm_labels,
                body=full_body,
            )
        )
    return chunks

def chunk_harm_cases(*, source: str, spec: dict, text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for heading, body in split_h2_sections(text):
        m = _HARM_CASE_HEADING_RE.match(heading)
        if not m:
            raise ValueError(
                f"harm-cases: heading {heading!r} missing '(chunk_id: ...)' suffix"
            )
        title = m.group(1).strip()
        chunk_id = m.group(2).strip()
        block_match = _HARM_CASE_LABEL_BLOCK_RE.search(body)
        if not block_match:
            raise ValueError(f"harm-cases: no 'Categorized harms:' block in {chunk_id!r}")
        raw_labels = _HARM_CASE_LABEL_LINE_RE.findall(block_match.group(1))
        if not raw_labels:
            raise ValueError(f"harm-cases: no labelled bullets in {chunk_id!r}")
        canonical = {lbl.lower(): lbl for lbl in SPECTRUM_LABELS}
        normalized: list[str] = []
        for lbl in raw_labels:
            if lbl.lower() not in canonical:
                raise UnmappedLabelError(
                    f"harm-cases: label {lbl!r} in {chunk_id!r} is not a Spectrum label"
                )
            normalized.append(canonical[lbl.lower()])
        harm_labels = sorted(set(normalized))
        full_body = _incident_body(original_label=title, body=body)
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                source=source,
                source_full_title=spec["title"],
                chunk_type=spec["chunk_type"],
                original_label=title,
                harm_labels=harm_labels,
                body=full_body,
            )
        )
    return chunks

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")

def _split_body_paragraphs(header_line: str, rest: str) -> list[str]:
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(rest) if p.strip()]
    parts: list[list[str]] = []
    current: list[str] = []
    current_tokens = count_tokens(header_line) + 2
    for para in paragraphs:
        para_tokens = count_tokens(para) + 2
        if current and current_tokens + para_tokens > TOKEN_SOFT_CAP:
            parts.append(current)
            current = []
            current_tokens = count_tokens(header_line) + 2
        current.append(para)
        current_tokens += para_tokens
    if current:
        parts.append(current)
    return [f"{header_line}\n\n" + "\n\n".join(part) for part in parts]

def enforce_bounds(chunks: Iterable[Chunk]) -> list[Chunk]:
    out: list[Chunk] = []
    for ch in chunks:
        n = count_tokens(ch.body)
        if n < TOKEN_FLOOR:
            log.warning(
                "below-floor chunk %s (%d tokens < %d); emitting as-is",
                ch.chunk_id, n, TOKEN_FLOOR,
            )
        if n <= TOKEN_HARD_CAP:
            out.append(ch)
            continue
        log.warning(
            "splitting chunk %s (%d tokens > hard cap %d)",
            ch.chunk_id, n, TOKEN_HARD_CAP,
        )
        header_line, _, rest = ch.body.partition("\n\n")
        part_bodies = _split_body_paragraphs(header_line, rest)
        for i, part_body in enumerate(part_bodies, start=1):
            out.append(
                Chunk(
                    chunk_id=f"{ch.chunk_id}__part{i}",
                    source=ch.source,
                    source_full_title=ch.source_full_title,
                    chunk_type=ch.chunk_type,
                    original_label=ch.original_label,
                    harm_labels=list(ch.harm_labels),
                    body=part_body,
                    stakeholders=list(ch.stakeholders),
                    part_of=ch.chunk_id,
                )
            )
    return out

REQUIRED_FIELDS = (
    "chunk_id", "source", "source_full_title", "chunk_type",
    "original_label", "body",
)

def validate(chunks: list[Chunk]) -> None:
    seen: set[str] = set()
    for ch in chunks:
        for f in REQUIRED_FIELDS:
            val = getattr(ch, f)
            if val in (None, "", []):
                raise ValueError(f"chunk {ch.chunk_id!r}: required field {f!r} is empty")
        if ch.chunk_type not in CHUNK_TYPES:
            raise ValueError(f"chunk {ch.chunk_id!r}: unknown chunk_type {ch.chunk_type!r}")
        bad = [lbl for lbl in ch.harm_labels if lbl not in SPECTRUM_LABELS]
        if bad:
            raise UnmappedLabelError(f"chunk {ch.chunk_id!r}: bad harm_labels {bad!r}")
        if ch.harm_labels != sorted(set(ch.harm_labels)):
            raise ValueError(f"chunk {ch.chunk_id!r}: harm_labels not sorted/deduped")
        if ch.chunk_id in seen:
            raise ValueError(f"duplicate chunk_id {ch.chunk_id!r}")
        seen.add(ch.chunk_id)

def build_chunks() -> list[Chunk]:
    mapping = load_mapping()
    overrides = load_overrides()
    all_chunks: list[Chunk] = []
    for source, spec in SOURCES.items():
        path = CLEANED_ROOT / spec["path"]
        text = path.read_text()
        if source == "harm-cases":
            chunks = chunk_harm_cases(source=source, spec=spec, text=text)
        else:
            chunks = chunk_qualitative(
                source=source, spec=spec, text=text,
                mapping=mapping, overrides=overrides,
            )
        all_chunks.extend(chunks)
    all_chunks.extend(build_aiaaic_chunks())
    all_chunks = enforce_bounds(all_chunks)
    all_chunks.sort(key=lambda c: c.chunk_id)
    validate(all_chunks)
    return all_chunks

def write_chunks(chunks: list[Chunk], path: Path = OUTPUT_FILE) -> None:
    payload = [c.to_dict() for c in chunks]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

def summarize(chunks: list[Chunk]) -> None:
    by_source: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for ch in chunks:
        by_source[ch.source] = by_source.get(ch.source, 0) + 1
        by_type[ch.chunk_type] = by_type.get(ch.chunk_type, 0) + 1
    log.info("total chunks: %d", len(chunks))
    log.info("by source: %s", dict(sorted(by_source.items())))
    log.info("by chunk_type: %s", dict(sorted(by_type.items())))

def main() -> None:
    chunks = build_chunks()
    write_chunks(chunks)
    summarize(chunks)
    log.info("wrote %s", OUTPUT_FILE)

if __name__ == "__main__":
    main()
