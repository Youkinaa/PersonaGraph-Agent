from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.domains.career import service as career_service
from app.domains.documents import service as document_service
from app.domains.documents.jobs import enqueue_parse_document


templates = Jinja2Templates(directory=str(get_settings().templates_dir))
router = APIRouter(include_in_schema=False)


def redirect_to(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/documents")
def documents_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="documents/index.html",
        context={
            "request": request,
            "settings": get_settings(),
            "phase": "Phase 3",
            "documents": document_service.list_documents(db),
            "counts": document_service.count_documents(db),
            "profiles": career_service.list_resume_profiles(db, limit=100),
        },
    )


@router.post("/documents/upload")
def upload_document_page(
    file: UploadFile = File(...),
    doc_type: str = Form("generic"),
    title: str | None = Form(None),
    resume_profile_id: str | None = Form(None),
    resume_version_label: str = Form("uploaded"),
    company: str | None = Form(None),
    location: str | None = Form(None),
    source_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    document = document_service.create_document_from_upload(db, file.file, file.filename or "document.txt", doc_type, title)
    link_document_to_career(
        db,
        document.id,
        doc_type,
        document.title,
        resume_profile_id=resume_profile_id,
        resume_version_label=resume_version_label,
        company=company,
        location=location,
        source_url=source_url,
    )
    enqueue_parse_document(db, document.id)
    return redirect_to("/documents")


@router.post("/documents/text")
def create_text_document_page(
    title: str = Form(...),
    doc_type: str = Form("generic"),
    content: str = Form(...),
    resume_profile_id: str | None = Form(None),
    resume_version_label: str = Form("uploaded"),
    company: str | None = Form(None),
    location: str | None = Form(None),
    source_url: str | None = Form(None),
    db: Session = Depends(get_db),
):
    document = document_service.create_document_from_text(db, title, doc_type, content)
    link_document_to_career(
        db,
        document.id,
        doc_type,
        document.title,
        resume_profile_id=resume_profile_id,
        resume_version_label=resume_version_label,
        company=company,
        location=location,
        source_url=source_url,
    )
    enqueue_parse_document(db, document.id)
    return redirect_to("/documents")


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
        career_service.create_resume_version(
            db,
            profile_id=resume_profile_id,
            version_label=resume_version_label,
            document_id=document_id,
            source_type="document",
        )
    if doc_type == "jd":
        career_service.create_job_posting(
            db,
            title=title,
            company=company,
            location=location,
            source_url=source_url,
            document_id=document_id,
        )
