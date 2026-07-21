from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SPECTRUM_LABELS: frozenset[str] = frozenset({
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
})

CHUNK_TYPES: frozenset[str] = frozenset({
    "real-incident",
    "qualitative-finding",
})

class UnmappedLabelError(ValueError):
    pass

@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    source: str
    source_full_title: str
    chunk_type: str
    harm_labels: list[str]
    body: str
    similarity: float

@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source: str
    source_full_title: str
    chunk_type: str
    original_label: str
    harm_labels: list[str]
    body: str
    stakeholders: list[str] = field(default_factory=list)
    part_of: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "source_full_title": self.source_full_title,
            "chunk_type": self.chunk_type,
            "original_label": self.original_label,
            "harm_labels": list(self.harm_labels),
            "stakeholders": list(self.stakeholders),
            "part_of": self.part_of,
            "body": self.body,
        }
