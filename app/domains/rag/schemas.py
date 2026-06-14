from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    score: float
    source: str
    rank: int


@dataclass
class FusedHit:
    chunk_id: str
    score: float = 0.0
    sources: list[str] = field(default_factory=list)
    source_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    document_id: str
    section_id: str
    title: str
    doc_type: str
    section_path: str | None
    content: str
    chunk_index: int
    embedding: list[float]
