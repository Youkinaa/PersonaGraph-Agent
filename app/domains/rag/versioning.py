from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.db.models import Document


@dataclass(frozen=True)
class DocumentVersionStatus:
    document_id: str
    parse_version: str | None
    index_version: str | None
    current_parse_version: str
    current_index_version: str
    parse_stale: bool
    index_stale: bool
    recommended_action: str


def build_parse_strategy(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return {
        "schema": "parse_strategy_v1",
        "parser_provider": settings.document_parser_provider,
        "parse_strategy_version": settings.document_parse_strategy_version,
        "text_extraction_mode": settings.document_text_extraction_mode,
        "parent_splitter": "simple_parent_sections",
        "parent_target_chars": settings.document_parent_target_chars,
        "child_splitter": "simple_child_chunks",
        "child_chunk_size": settings.document_child_chunk_size,
        "child_chunk_overlap": settings.document_child_chunk_overlap,
        "ocr": {
            "enabled": settings.document_ocr_enabled,
            "provider": settings.document_ocr_provider,
            "image_extensions": settings.document_image_extensions,
        },
        "multimodal": {
            "enabled": settings.document_multimodal_enabled,
            "modalities": ["image_text"] if settings.document_multimodal_enabled else [],
            "audio_supported": False,
        },
    }


def build_index_strategy(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return {
        "schema": "index_strategy_v1",
        "depends_on_parse_version": current_parse_version(settings),
        "embedding": {
            "provider": settings.rag_embedding_provider,
            "model": settings.embedding_model_id,
            "dimension": settings.rag_embedding_dim,
        },
        "bm25": {
            "provider": "elasticsearch",
            "index": settings.rag_es_index,
        },
        "vector": {
            "provider": "milvus",
            "collection": settings.rag_milvus_collection,
            "metric": "COSINE",
        },
        "fusion": {
            "algorithm": "rrf_v1",
        },
        "rerank": {
            "enabled": settings.rag_rerank_enabled,
            "model": settings.rerank_model_id,
            "candidate_multiplier": settings.rag_rerank_candidate_multiplier,
            "document_max_chars": settings.rag_rerank_document_max_chars,
        },
    }


def current_parse_version(settings: Settings | None = None) -> str:
    return strategy_version("parse", build_parse_strategy(settings))


def current_index_version(settings: Settings | None = None) -> str:
    return strategy_version("index", build_index_strategy(settings))


def strategy_version(prefix: str, strategy: dict[str, Any]) -> str:
    payload = json.dumps(strategy, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    schema = strategy.get("schema", "strategy")
    return f"{schema}:{prefix}:{digest}"


def document_version_status(document: Document, settings: Settings | None = None) -> DocumentVersionStatus:
    settings = settings or get_settings()
    current_parse = current_parse_version(settings)
    current_index = current_index_version(settings)
    metadata = document.metadata_ or {}
    parse_version = metadata.get("parse_version")
    index_version = metadata.get("index_version")

    parse_stale = document.parse_status == "parsed" and parse_version != current_parse
    index_stale = (
        document.parse_status == "parsed"
        and document.index_status in {"indexed", "partially_indexed", "local_only"}
        and index_version != current_index
    )
    if parse_stale:
        action = "reparse"
    elif document.parse_status == "parsed" and (
        document.index_status in {"not_indexed", "ready_for_indexing", "empty"} or index_stale
    ):
        action = "reindex"
    else:
        action = "none"

    return DocumentVersionStatus(
        document_id=document.id,
        parse_version=parse_version,
        index_version=index_version,
        current_parse_version=current_parse,
        current_index_version=current_index,
        parse_stale=parse_stale,
        index_stale=index_stale,
        recommended_action=action,
    )
