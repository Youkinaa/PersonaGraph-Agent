from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.career import service


router = APIRouter(prefix="/api/career", tags=["career"])


class ResumeProfileCreate(BaseModel):
    title: str
    target_role: str | None = None
    summary: str | None = None


class ResumeVersionCreate(BaseModel):
    profile_id: str
    version_label: str = "v1"
    content: str | None = None
    is_primary: bool = False
    document_id: str | None = None
    source_type: str = "manual"


class JobPostingCreate(BaseModel):
    title: str
    company: str | None = None
    location: str | None = None
    description: str | None = None
    requirements: str | None = None
    source_url: str | None = None
    remote_policy: str | None = None
    employment_type: str | None = None
    document_id: str | None = None


class JobSubscriptionCreate(BaseModel):
    name: str
    query: str
    locations: list[str] = Field(default_factory=list)
    remote_policy: str | None = None
    frequency: str = "daily"


class ApplicationCreate(BaseModel):
    job_posting_id: str
    resume_version_id: str | None = None
    status: str = "interested"
    source: str | None = None
    notes: str | None = None
    next_action_at: datetime | None = None


class CareerGoalCreate(BaseModel):
    title: str
    target_role: str | None = None
    target_date: datetime | None = None
    description: str | None = None
    success_criteria: list[str] = Field(default_factory=list)


class LearningGoalCreate(BaseModel):
    title: str
    target_skill: str | None = None
    target_date: datetime | None = None
    description: str | None = None
    success_criteria: list[str] = Field(default_factory=list)


class NotificationCreate(BaseModel):
    title: str
    body: str
    notification_type: str = "manual"
    related_entity_type: str | None = None
    related_entity_id: str | None = None


def row_summary(row) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


@router.get("/resumes")
def list_resumes(db: Session = Depends(get_db)) -> dict:
    return {
        "profiles": [
            row_summary(profile)
            | {
                "title": profile.title,
                "target_role": profile.target_role,
                "summary": profile.summary,
                "versions": [
                    {
                        "id": version.id,
                        "version_label": version.version_label,
                        "status": version.status,
                        "is_primary": version.is_primary,
                        "document_id": version.document_id,
                        "source_type": version.source_type,
                    }
                    for version in profile.versions
                ],
            }
            for profile in service.list_resume_profiles(db)
        ]
    }


@router.post("/resume-profiles", status_code=status.HTTP_201_CREATED)
def create_resume_profile(payload: ResumeProfileCreate, db: Session = Depends(get_db)) -> dict:
    profile = service.create_resume_profile(db, payload.title, payload.target_role, payload.summary)
    return row_summary(profile) | {"title": profile.title, "target_role": profile.target_role}


@router.delete("/resume-profiles/{profile_id}")
def delete_resume_profile(profile_id: str, db: Session = Depends(get_db)) -> dict:
    deleted = service.delete_resume_profile(db, profile_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume profile not found.")
    return {"deleted": True, "profile_id": profile_id}


@router.post("/resume-versions", status_code=status.HTTP_201_CREATED)
def create_resume_version(payload: ResumeVersionCreate, db: Session = Depends(get_db)) -> dict:
    version = service.create_resume_version(
        db,
        payload.profile_id,
        payload.version_label,
        payload.content,
        payload.is_primary,
        document_id=payload.document_id,
        source_type=payload.source_type,
    )
    return row_summary(version) | {
        "version_label": version.version_label,
        "profile_id": version.profile_id,
        "document_id": version.document_id,
        "source_type": version.source_type,
    }


@router.delete("/resume-versions/{version_id}")
def delete_resume_version(version_id: str, db: Session = Depends(get_db)) -> dict:
    deleted = service.delete_resume_version(db, version_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found.")
    return {"deleted": True, "version_id": version_id}


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)) -> dict:
    return {
        "job_postings": [
            row_summary(job)
            | {
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "status": job.status,
            }
            for job in service.list_job_postings(db)
        ],
        "subscriptions": [
            row_summary(subscription)
            | {
                "name": subscription.name,
                "query": subscription.query,
                "locations": subscription.locations,
                "enabled": subscription.enabled,
            }
            for subscription in service.list_job_subscriptions(db)
        ],
    }


@router.post("/job-postings", status_code=status.HTTP_201_CREATED)
def create_job_posting(payload: JobPostingCreate, db: Session = Depends(get_db)) -> dict:
    job = service.create_job_posting(db, **payload.model_dump())
    return row_summary(job) | {"title": job.title, "company": job.company, "status": job.status}


@router.post("/job-subscriptions", status_code=status.HTTP_201_CREATED)
def create_job_subscription(payload: JobSubscriptionCreate, db: Session = Depends(get_db)) -> dict:
    subscription = service.create_job_subscription(db, **payload.model_dump())
    return row_summary(subscription) | {"name": subscription.name, "query": subscription.query}


@router.get("/applications")
def list_applications(db: Session = Depends(get_db)) -> dict:
    return {
        "applications": [
            row_summary(application)
            | {
                "status": application.status,
                "job_title": application.job_posting.title,
                "company": application.job_posting.company,
                "resume_version_id": application.resume_version_id,
            }
            for application in service.list_applications(db)
        ]
    }


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)) -> dict:
    application = service.create_application(db, **payload.model_dump())
    return row_summary(application) | {"status": application.status, "job_posting_id": application.job_posting_id}


@router.get("/goals")
def list_goals(db: Session = Depends(get_db)) -> dict:
    return {
        "career_goals": [
            row_summary(goal) | {"title": goal.title, "target_role": goal.target_role, "status": goal.status}
            for goal in service.list_career_goals(db)
        ],
        "learning_goals": [
            row_summary(goal) | {"title": goal.title, "target_skill": goal.target_skill, "status": goal.status}
            for goal in service.list_learning_goals(db)
        ],
    }


@router.post("/career-goals", status_code=status.HTTP_201_CREATED)
def create_career_goal(payload: CareerGoalCreate, db: Session = Depends(get_db)) -> dict:
    goal = service.create_career_goal(db, **payload.model_dump())
    return row_summary(goal) | {"title": goal.title, "target_role": goal.target_role}


@router.post("/learning-goals", status_code=status.HTTP_201_CREATED)
def create_learning_goal(payload: LearningGoalCreate, db: Session = Depends(get_db)) -> dict:
    goal = service.create_learning_goal(db, **payload.model_dump())
    return row_summary(goal) | {"title": goal.title, "target_skill": goal.target_skill}


@router.get("/notifications")
def list_notifications(db: Session = Depends(get_db)) -> dict:
    return {
        "notifications": [
            row_summary(notification)
            | {
                "title": notification.title,
                "body": notification.body,
                "notification_type": notification.notification_type,
                "status": notification.status,
            }
            for notification in service.list_notifications(db)
        ]
    }


@router.post("/notifications", status_code=status.HTTP_201_CREATED)
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db)) -> dict:
    notification = service.create_notification(db, **payload.model_dump())
    return row_summary(notification) | {
        "title": notification.title,
        "notification_type": notification.notification_type,
        "status": notification.status,
    }
