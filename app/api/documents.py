from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.career.service import create_job_posting, create_resume_version
from app.domains.documents.jobs import enqueue_parse_document
from app.domains.documents import service as document_service


router = APIRouter(prefix="/api/documents", tags=["documents"])


class TextDocumentCreate(BaseModel):
    title: str
    doc_type: str = "generic"
    content: str
    resume_profile_id: str | None = None
    resume_version_label: str = "uploaded"
    company: str | None = None
    location: str | None = None
    source_url: str | None = None


def serialize_document(document) -> dict:
    return {
        "id": document.id,
        "title": document.title,
        "doc_type": document.doc_type,
        "source_type": document.source_type,
        "parse_status": document.parse_status,
        "index_status": document.index_status,
        "section_count": len(document.sections) if getattr(document, "sections", None) is not None else None,
        "chunk_count": len(document.chunks) if getattr(document, "chunks", None) is not None else None,
    }


@router.get("")
def list_documents(db: Session = Depends(get_db)) -> dict:
    return {"documents": [serialize_document(document) for document in document_service.list_documents(db)]}


@router.get("/{document_id}")
def read_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    document = document_service.get_document(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return serialize_document(document)


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("generic"),
    title: str | None = Form(None),
    resume_profile_id: str | None = Form(None),
    resume_version_label: str = Form("uploaded"),
    company: str | None = Form(None),
    location: str | None = Form(None),
    source_url: str | None = Form(None),
    db: Session = Depends(get_db),
) -> dict:
    try:
        document = document_service.create_document_from_upload(db, file.file, file.filename or "document.txt", doc_type, title)
        link_document_to_career(
            db,
            document_id=document.id,
            doc_type=doc_type,
            title=document.title,
            resume_profile_id=resume_profile_id,
            resume_version_label=resume_version_label,
            company=company,
            location=location,
            source_url=source_url,
        )
        task_run = enqueue_parse_document(db, document.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"document": serialize_document(document), "task_run_id": task_run.id, "celery_task_id": task_run.celery_task_id}


@router.post("/text", status_code=status.HTTP_202_ACCEPTED)
def create_text_document(payload: TextDocumentCreate, db: Session = Depends(get_db)) -> dict:
    document = document_service.create_document_from_text(db, payload.title, payload.doc_type, payload.content)
    link_document_to_career(
        db,
        document_id=document.id,
        doc_type=payload.doc_type,
        title=document.title,
        resume_profile_id=payload.resume_profile_id,
        resume_version_label=payload.resume_version_label,
        company=payload.company,
        location=payload.location,
        source_url=payload.source_url,
    )
    task_run = enqueue_parse_document(db, document.id)
    return {"document": serialize_document(document), "task_run_id": task_run.id, "celery_task_id": task_run.celery_task_id}


def link_document_to_career(
    db: Session,
    document_id: str,
    doc_type: str,
    title: str,
    resume_profile_id: str | None = None,
    resume_version_label: str = "uploaded",
    company: str | None = None,
    location: str | None = None,
    source_url: str | None = None,
) -> None:
    if doc_type == "resume" and resume_profile_id:
        create_resume_version(
            db,
            profile_id=resume_profile_id,
            version_label=resume_version_label,
            document_id=document_id,
            source_type="document",
            is_primary=False,
        )
    if doc_type == "jd":
        create_job_posting(
            db,
            title=title,
            company=company,
            location=location,
            source_url=source_url,
            document_id=document_id,
        )
