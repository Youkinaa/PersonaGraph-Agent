from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.rag.jobs import enqueue_index_document, enqueue_reindex_document, enqueue_reindex_stale_documents
from app.domains.rag.service import (
    check_rag_indexes,
    index_ready_documents,
    index_status_summary,
    search_documents,
)


router = APIRouter(prefix="/api/rag", tags=["rag"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=8, ge=1, le=20)
    doc_type: str | None = None
    rerank: bool | None = None


@router.post("/documents/{document_id}/index", status_code=status.HTTP_202_ACCEPTED)
def enqueue_document_index(document_id: str, db: Session = Depends(get_db)) -> dict:
    task_run = enqueue_index_document(db, document_id)
    return {
        "task_run_id": task_run.id,
        "celery_task_id": task_run.celery_task_id,
        "document_id": document_id,
    }


@router.post("/documents/{document_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
def enqueue_document_reindex(document_id: str, db: Session = Depends(get_db)) -> dict:
    task_run = enqueue_reindex_document(db, document_id)
    return {
        "task_run_id": task_run.id,
        "celery_task_id": task_run.celery_task_id,
        "document_id": document_id,
    }


@router.post("/index-ready")
def index_ready(limit: int = 20, db: Session = Depends(get_db)) -> dict:
    return index_ready_documents(db, limit=limit)


@router.post("/reindex-stale", status_code=status.HTTP_202_ACCEPTED)
def reindex_stale(limit: int = 20, db: Session = Depends(get_db)) -> dict:
    return enqueue_reindex_stale_documents(db, limit=limit)


@router.get("/indexes/health")
def indexes_health() -> dict:
    return check_rag_indexes()


@router.get("/indexes/status")
def indexes_status(db: Session = Depends(get_db)) -> dict:
    return index_status_summary(db)


@router.post("/search")
def search(payload: SearchRequest, db: Session = Depends(get_db)) -> dict:
    result = search_documents(db, payload.query, top_k=payload.top_k, doc_type=payload.doc_type, rerank=payload.rerank)
    if result.get("errors", {}).get("query"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["errors"]["query"])
    return result
