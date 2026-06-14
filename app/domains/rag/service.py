from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.models import Document, DocumentChunk, DocumentSection
from app.domains.rag.embeddings import embed_texts, tokenize
from app.domains.rag.fusion import reciprocal_rank_fusion
from app.domains.rag.indexes import ElasticsearchChunkIndex, MilvusChunkIndex
from app.domains.rag.rerankers import rerank_evidence_pack
from app.domains.rag.schemas import ChunkRecord, FusedHit, RetrievalHit
from app.domains.rag.versioning import (
    build_index_strategy,
    current_index_version,
    current_parse_version,
    document_version_status,
)


def build_chunk_records(document: Document) -> list[ChunkRecord]:
    settings = get_settings()
    chunks = sorted(document.chunks, key=lambda item: item.chunk_index)
    embeddings = embed_texts([chunk.content for chunk in chunks], settings=settings)
    records: list[ChunkRecord] = []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        section = chunk.section
        records.append(
            ChunkRecord(
                chunk_id=chunk.id,
                document_id=document.id,
                section_id=chunk.section_id,
                title=document.title,
                doc_type=document.doc_type,
                section_path=section.section_path if section else None,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                embedding=embedding,
            )
        )
    return records


def get_document_for_indexing(db: Session, document_id: str) -> Document | None:
    statement = (
        select(Document)
        .where(Document.id == document_id)
        .options(
            selectinload(Document.chunks).selectinload(DocumentChunk.section),
            selectinload(Document.sections),
        )
    )
    return db.scalar(statement)


def index_document(db: Session, document_id: str) -> dict:
    settings = get_settings()
    document = get_document_for_indexing(db, document_id)
    if document is None:
        raise ValueError(f"Document not found: {document_id}")
    if document.parse_status != "parsed":
        raise ValueError("Document must be parsed before indexing.")
    if not document.chunks:
        document.index_status = "empty"
        db.commit()
        return {
            "document_id": document.id,
            "index_status": document.index_status,
            "chunk_count": 0,
            "results": {},
            "errors": {},
        }

    index_strategy = build_index_strategy(settings)
    index_version = current_index_version(settings)
    parse_version = current_parse_version(settings)
    version_status = document_version_status(document, settings)
    records = build_chunk_records(document)
    results: dict[str, int | str] = {}
    errors: dict[str, str] = {}

    try:
        results["elasticsearch"] = ElasticsearchChunkIndex(settings).index_chunks(records)
    except Exception as exc:
        errors["elasticsearch"] = str(exc)

    try:
        results["milvus"] = MilvusChunkIndex(settings).index_chunks(records)
    except Exception as exc:
        errors["milvus"] = str(exc)

    es_ok = "elasticsearch" in results
    milvus_ok = "milvus" in results
    for chunk in document.chunks:
        chunk.bm25_status = "indexed" if es_ok else "unavailable"
        chunk.embedding_status = "indexed" if milvus_ok else "unavailable"
        chunk.metadata_ = {
            **(chunk.metadata_ or {}),
            "parse_version": (chunk.metadata_ or {}).get("parse_version") or parse_version,
            "index_version": index_version,
        }

    if es_ok and milvus_ok:
        document.index_status = "indexed"
    elif es_ok or milvus_ok:
        document.index_status = "partially_indexed"
    else:
        document.index_status = "local_only"

    document.metadata_ = {
        **(document.metadata_ or {}),
        "index_version": index_version,
        "index_strategy": index_strategy,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "index_warnings": {
            "parse_stale": version_status.parse_stale,
            "parse_version": version_status.parse_version,
            "current_parse_version": parse_version,
        },
        "index_results": results,
        "index_errors": errors,
    }
    db.commit()

    return {
        "document_id": document.id,
        "index_status": document.index_status,
        "chunk_count": len(records),
        "index_version": index_version,
        "parse_version": document.metadata_.get("parse_version"),
        "parse_stale": version_status.parse_stale,
        "results": results,
        "errors": errors,
    }


def reindex_document(db: Session, document_id: str) -> dict:
    document = get_document_for_indexing(db, document_id)
    if document is None:
        raise ValueError(f"Document not found: {document_id}")
    if document.parse_status != "parsed":
        raise ValueError("Document must be parsed before re-indexing.")

    document.index_status = "reindexing"
    for chunk in document.chunks:
        chunk.bm25_status = "pending"
        chunk.embedding_status = "pending"
        chunk.metadata_ = {**(chunk.metadata_ or {}), "index_version": None}
    db.commit()

    cleanup = delete_document_indexes(document_id)
    result = index_document(db, document_id)
    return {
        **result,
        "reindexed": True,
        "cleanup": cleanup,
    }


def index_ready_documents(db: Session, limit: int = 20) -> dict:
    statement = (
        select(Document)
        .where(Document.parse_status == "parsed")
        .where(Document.index_status.in_(["ready_for_indexing", "not_indexed", "local_only", "partially_indexed"]))
        .order_by(desc(Document.updated_at))
        .limit(limit)
    )
    documents = list(db.scalars(statement))
    indexed: list[dict] = []
    errors: list[dict] = []
    for document in documents:
        try:
            indexed.append(index_document(db, document.id))
        except Exception as exc:
            errors.append({"document_id": document.id, "error": str(exc)})
    return {"indexed": indexed, "errors": errors, "attempted": len(documents)}


def check_rag_indexes() -> dict:
    settings = get_settings()
    checks = {
        "elasticsearch": ElasticsearchChunkIndex(settings).health(),
        "milvus": MilvusChunkIndex(settings).health(),
    }
    status = "ok" if all(item["status"] == "ok" for item in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


def delete_document_indexes(document_id: str) -> dict:
    settings = get_settings()
    results: dict[str, dict] = {}
    errors: dict[str, str] = {}

    try:
        results["elasticsearch"] = ElasticsearchChunkIndex(settings).delete_document(document_id)
    except Exception as exc:
        errors["elasticsearch"] = str(exc)

    try:
        results["milvus"] = MilvusChunkIndex(settings).delete_document(document_id)
    except Exception as exc:
        errors["milvus"] = str(exc)

    return {
        "document_id": document_id,
        "results": results,
        "errors": errors,
        "status": "ok" if not errors else "partial",
    }


def index_status_summary(db: Session) -> dict:
    document_rows = db.execute(
        select(Document.index_status, func.count(Document.id)).group_by(Document.index_status)
    ).all()
    embedding_rows = db.execute(
        select(DocumentChunk.embedding_status, func.count(DocumentChunk.id)).group_by(DocumentChunk.embedding_status)
    ).all()
    bm25_rows = db.execute(
        select(DocumentChunk.bm25_status, func.count(DocumentChunk.id)).group_by(DocumentChunk.bm25_status)
    ).all()
    ready_documents = db.scalar(
        select(func.count(Document.id))
        .where(Document.parse_status == "parsed")
        .where(Document.index_status.in_(["ready_for_indexing", "not_indexed", "local_only", "partially_indexed"]))
    )
    settings = get_settings()
    version_documents = list(db.scalars(select(Document).where(Document.parse_status == "parsed").limit(1000)))
    version_statuses = [document_version_status(document, settings) for document in version_documents]
    parse_stale = [status for status in version_statuses if status.parse_stale]
    index_stale = [status for status in version_statuses if status.index_stale]
    return {
        "documents": {status or "unknown": count for status, count in document_rows},
        "embeddings": {status or "unknown": count for status, count in embedding_rows},
        "bm25": {status or "unknown": count for status, count in bm25_rows},
        "ready_documents": ready_documents or 0,
        "current_parse_version": current_parse_version(settings),
        "current_index_version": current_index_version(settings),
        "parse_stale_documents": len(parse_stale),
        "index_stale_documents": len(index_stale),
        "stale_documents": len({status.document_id for status in parse_stale + index_stale}),
    }


def list_stale_index_documents(db: Session, limit: int = 20) -> list[Document]:
    settings = get_settings()
    statement = (
        select(Document)
        .where(Document.parse_status == "parsed")
        .where(Document.index_status.in_(["indexed", "partially_indexed", "local_only", "ready_for_indexing", "not_indexed"]))
        .order_by(desc(Document.updated_at))
        .limit(max(limit * 5, limit))
    )
    stale: list[Document] = []
    for document in db.scalars(statement):
        status = document_version_status(document, settings)
        if status.recommended_action == "reindex":
            stale.append(document)
        if len(stale) >= limit:
            break
    return stale


def search_documents(
    db: Session,
    query: str,
    top_k: int = 8,
    doc_type: str | None = None,
    rerank: bool | None = None,
) -> dict:
    query = query.strip()
    if not query:
        return {"query": query, "evidence": [], "retrievers": {}, "errors": {"query": "Query is empty."}}

    settings = get_settings()
    rerank_enabled = settings.rag_rerank_enabled if rerank is None else rerank
    candidate_count = min(max(top_k, top_k * max(1, settings.rag_rerank_candidate_multiplier)), 50)
    result_sets: list[list[RetrievalHit]] = []
    retrievers: dict[str, int | str] = {}
    errors: dict[str, str] = {}

    try:
        bm25_hits = ElasticsearchChunkIndex(settings).search(query, top_k=candidate_count, doc_type=doc_type)
        result_sets.append(bm25_hits)
        retrievers["bm25"] = len(bm25_hits)
    except Exception as exc:
        errors["bm25"] = str(exc)

    try:
        vector_hits = MilvusChunkIndex(settings).search(query, top_k=candidate_count)
        if doc_type:
            vector_hits = filter_hits_by_doc_type(db, vector_hits, doc_type)
        result_sets.append(vector_hits)
        retrievers["vector"] = len(vector_hits)
    except Exception as exc:
        errors["vector"] = str(exc)

    local_hits = local_keyword_search(db, query, top_k=candidate_count, doc_type=doc_type)
    result_sets.append(local_hits)
    retrievers["local"] = len(local_hits)

    fused_hits = reciprocal_rank_fusion(result_sets)[:candidate_count]
    evidence_candidates = build_evidence_pack(db, fused_hits)
    reranker = {
        "enabled": rerank_enabled,
        "model": settings.rerank_model_id,
        "candidate_count": len(evidence_candidates),
        "returned": min(top_k, len(evidence_candidates)),
        "status": "skipped",
    }
    if rerank_enabled:
        try:
            evidence, reranker = rerank_evidence_pack(query, evidence_candidates, top_k=top_k, settings=settings)
        except Exception as exc:
            errors["rerank"] = str(exc)
            reranker["status"] = "failed"
            reranker["fallback"] = "rrf"
            evidence = evidence_candidates[:top_k]
    else:
        evidence = evidence_candidates[:top_k]

    return {
        "query": query,
        "top_k": top_k,
        "candidate_count": candidate_count,
        "retrievers": retrievers,
        "reranker": reranker,
        "errors": errors,
        "evidence": evidence,
    }


def filter_hits_by_doc_type(db: Session, hits: list[RetrievalHit], doc_type: str) -> list[RetrievalHit]:
    if not hits:
        return []
    chunk_ids = [hit.chunk_id for hit in hits]
    statement = (
        select(DocumentChunk.id)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_(chunk_ids))
        .where(Document.doc_type == doc_type)
    )
    allowed = set(db.scalars(statement))
    return [hit for hit in hits if hit.chunk_id in allowed]


def local_keyword_search(db: Session, query: str, top_k: int = 8, doc_type: str | None = None) -> list[RetrievalHit]:
    tokens = tokenize(query) or [query.lower()]
    statement = (
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .options(selectinload(DocumentChunk.document), selectinload(DocumentChunk.section))
        .order_by(desc(DocumentChunk.updated_at))
        .limit(1000)
    )
    if doc_type:
        statement = statement.where(Document.doc_type == doc_type)

    scored: list[tuple[str, float]] = []
    for chunk in db.scalars(statement):
        content = chunk.content.lower()
        title = (chunk.document.title if chunk.document else "").lower()
        section = (chunk.section.section_path if chunk.section and chunk.section.section_path else "").lower()
        score = 0.0
        for token in tokens:
            score += content.count(token) * 2
            score += title.count(token) * 3
            score += section.count(token)
        if score > 0:
            scored.append((chunk.id, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return [
        RetrievalHit(chunk_id=chunk_id, score=score, source="local", rank=index)
        for index, (chunk_id, score) in enumerate(scored[:top_k])
    ]


def build_evidence_pack(db: Session, hits: list[FusedHit]) -> list[dict]:
    if not hits:
        return []
    chunk_ids = [hit.chunk_id for hit in hits]
    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.id.in_(chunk_ids))
        .options(
            selectinload(DocumentChunk.document),
            selectinload(DocumentChunk.section).selectinload(DocumentSection.document),
        )
    )
    chunks = {chunk.id: chunk for chunk in db.scalars(statement)}
    evidence: list[dict] = []
    for hit in hits:
        chunk = chunks.get(hit.chunk_id)
        if chunk is None:
            continue
        document = chunk.document
        section = chunk.section
        evidence.append(
            {
                "chunk_id": chunk.id,
                "rrf_score": round(hit.score, 6),
                "sources": hit.sources,
                "source_scores": hit.source_scores,
                "chunk": {
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "start_offset": chunk.start_offset,
                    "end_offset": chunk.end_offset,
                },
                "parent": {
                    "section_id": section.id if section else None,
                    "title": section.title if section else None,
                    "section_path": section.section_path if section else None,
                    "content": section.content if section else None,
                },
                "document": {
                    "document_id": document.id if document else chunk.document_id,
                    "title": document.title if document else None,
                    "doc_type": document.doc_type if document else None,
                },
            }
        )
    return evidence
