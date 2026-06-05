from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.domains.career import service
from app.domains.documents import service as document_service


templates = Jinja2Templates(directory=str(get_settings().templates_dir))
router = APIRouter(include_in_schema=False)


def redirect_to(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/resumes")
def resumes_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="career/resumes.html",
        context={
            "request": request,
            "settings": get_settings(),
            "phase": "Phase 2",
            "profiles": service.list_resume_profiles(db),
            "resume_documents": document_service.list_documents(db, limit=100, doc_type="resume"),
        },
    )


@router.post("/resumes/profiles")
def create_resume_profile(
    title: str = Form(...),
    target_role: str | None = Form(None),
    summary: str | None = Form(None),
    db: Session = Depends(get_db),
):
    service.create_resume_profile(db, title, target_role, summary)
    return redirect_to("/resumes")


@router.post("/resumes/versions")
def create_resume_version(
    profile_id: str = Form(...),
    version_label: str = Form("v1"),
    document_id: str | None = Form(None),
    content: str | None = Form(None),
    is_primary: bool = Form(False),
    db: Session = Depends(get_db),
):
    normalized_document_id = document_id or None
    source_type = "document" if normalized_document_id else "manual"
    service.create_resume_version(
        db,
        profile_id,
        version_label,
        content,
        is_primary,
        document_id=normalized_document_id,
        source_type=source_type,
    )
    return redirect_to("/resumes")


@router.post("/resumes/profiles/{profile_id}/delete")
def delete_resume_profile(profile_id: str, db: Session = Depends(get_db)):
    service.delete_resume_profile(db, profile_id)
    return redirect_to("/resumes")


@router.post("/resumes/versions/{version_id}/delete")
def delete_resume_version(version_id: str, db: Session = Depends(get_db)):
    service.delete_resume_version(db, version_id)
    return redirect_to("/resumes")


@router.get("/jobs")
def jobs_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="career/jobs.html",
        context={
            "request": request,
            "settings": get_settings(),
            "phase": "Phase 2",
            "job_postings": service.list_job_postings(db),
            "job_subscriptions": service.list_job_subscriptions(db),
        },
    )


@router.post("/jobs/postings")
def create_job_posting(
    title: str = Form(...),
    company: str | None = Form(None),
    location: str | None = Form(None),
    remote_policy: str | None = Form(None),
    employment_type: str | None = Form(None),
    source_url: str | None = Form(None),
    description: str | None = Form(None),
    requirements: str | None = Form(None),
    db: Session = Depends(get_db),
):
    service.create_job_posting(
        db,
        title=title,
        company=company,
        location=location,
        remote_policy=remote_policy,
        employment_type=employment_type,
        source_url=source_url,
        description=description,
        requirements=requirements,
    )
    return redirect_to("/jobs")


@router.post("/jobs/subscriptions")
def create_job_subscription(
    name: str = Form(...),
    query: str = Form(...),
    locations: str | None = Form(None),
    remote_policy: str | None = Form(None),
    frequency: str = Form("daily"),
    db: Session = Depends(get_db),
):
    service.create_job_subscription(
        db,
        name=name,
        query=query,
        locations=service.split_lines(locations),
        remote_policy=remote_policy,
        frequency=frequency,
    )
    return redirect_to("/jobs")


@router.get("/applications")
def applications_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="career/applications.html",
        context={
            "request": request,
            "settings": get_settings(),
            "phase": "Phase 2",
            "applications": service.list_applications(db),
            "job_postings": service.list_job_postings(db, limit=100),
            "resume_versions": service.list_resume_versions(db, limit=100),
        },
    )


@router.post("/applications")
def create_application(
    job_posting_id: str = Form(...),
    resume_version_id: str | None = Form(None),
    status_value: str = Form("interested", alias="status"),
    source: str | None = Form(None),
    next_action_at: str | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    service.create_application(
        db,
        job_posting_id=job_posting_id,
        resume_version_id=resume_version_id or None,
        status=status_value,
        source=source,
        next_action_at=service.parse_optional_date(next_action_at),
        notes=notes,
    )
    return redirect_to("/applications")


@router.get("/goals")
def goals_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="career/goals.html",
        context={
            "request": request,
            "settings": get_settings(),
            "phase": "Phase 2",
            "career_goals": service.list_career_goals(db),
            "learning_goals": service.list_learning_goals(db),
        },
    )


@router.post("/goals/career")
def create_career_goal(
    title: str = Form(...),
    target_role: str | None = Form(None),
    target_date: str | None = Form(None),
    description: str | None = Form(None),
    success_criteria: str | None = Form(None),
    db: Session = Depends(get_db),
):
    service.create_career_goal(
        db,
        title=title,
        target_role=target_role,
        target_date=service.parse_optional_date(target_date),
        description=description,
        success_criteria=service.split_lines(success_criteria),
    )
    return redirect_to("/goals")


@router.post("/goals/learning")
def create_learning_goal(
    title: str = Form(...),
    target_skill: str | None = Form(None),
    target_date: str | None = Form(None),
    description: str | None = Form(None),
    success_criteria: str | None = Form(None),
    db: Session = Depends(get_db),
):
    service.create_learning_goal(
        db,
        title=title,
        target_skill=target_skill,
        target_date=service.parse_optional_date(target_date),
        description=description,
        success_criteria=service.split_lines(success_criteria),
    )
    return redirect_to("/goals")


@router.get("/notifications")
def notifications_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="career/notifications.html",
        context={
            "request": request,
            "settings": get_settings(),
            "phase": "Phase 2",
            "notifications": service.list_notifications(db),
        },
    )


@router.post("/notifications")
def create_notification(
    title: str = Form(...),
    body: str = Form(...),
    notification_type: str = Form("manual"),
    db: Session = Depends(get_db),
):
    service.create_notification(db, title, body, notification_type=notification_type)
    return redirect_to("/notifications")
