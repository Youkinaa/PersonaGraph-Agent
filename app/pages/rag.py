from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.domains.rag.jobs import enqueue_reindex_stale_documents
from app.domains.rag.service import (
    check_rag_indexes,
    index_ready_documents,
    index_status_summary,
    search_documents,
)


templates = Jinja2Templates(directory=str(get_settings().templates_dir))
router = APIRouter(include_in_schema=False)


@router.get("/rag")
def rag_page(
    request: Request,
    query: str | None = Query(None),
    doc_type: str | None = Query(None),
    top_k: int = Query(8, ge=1, le=20),
    rerank_mode: str = Query("auto"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
):
    result = None
    rerank_override = {"on": True, "off": False}.get(rerank_mode)
    if query:
        result = search_documents(db, query, top_k=top_k, doc_type=doc_type or None, rerank=rerank_override)
    index_health = check_rag_indexes()
    index_summary = index_status_summary(db)
    return templates.TemplateResponse(
        request=request,
        name="rag/index.html",
        context={
            "request": request,
            "settings": settings,
            "phase": settings.app_phase_label,
            "query": query or "",
            "doc_type": doc_type or "",
            "top_k": top_k,
            "rerank_mode": rerank_mode,
            "result": result,
            "index_health": index_health,
            "index_summary": index_summary,
        },
    )


@router.post("/rag/index-ready")
def rag_index_ready(limit: int = Form(5), db: Session = Depends(get_db)):
    index_ready_documents(db, limit=limit)
    return RedirectResponse(url="/rag", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/rag/reindex-stale")
def rag_reindex_stale(limit: int = Form(5), db: Session = Depends(get_db)):
    enqueue_reindex_stale_documents(db, limit=limit)
    return RedirectResponse(url="/rag", status_code=status.HTTP_303_SEE_OTHER)
