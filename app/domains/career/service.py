from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Application,
    CareerGoal,
    JobPosting,
    JobSource,
    JobSubscription,
    LearningGoal,
    Notification,
    ResumeProfile,
    ResumeVersion,
)


def split_lines(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace(",", "\n").splitlines() if item.strip()]


def parse_optional_date(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def create_resume_profile(
    db: Session,
    title: str,
    target_role: str | None = None,
    summary: str | None = None,
) -> ResumeProfile:
    profile = ResumeProfile(title=title, target_role=target_role or None, summary=summary or None)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def create_resume_version(
    db: Session,
    profile_id: str,
    version_label: str,
    content: str | None = None,
    is_primary: bool = False,
    document_id: str | None = None,
    source_type: str = "manual",
) -> ResumeVersion:
    normalized_source_type = source_type or "manual"
    if document_id and normalized_source_type == "manual":
        normalized_source_type = "document"

    if is_primary:
        for version in db.scalars(select(ResumeVersion).where(ResumeVersion.profile_id == profile_id)):
            version.is_primary = False
    version = ResumeVersion(
        profile_id=profile_id,
        document_id=document_id or None,
        version_label=version_label,
        content=content or None,
        is_primary=is_primary,
        source_type=normalized_source_type,
        status="draft",
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def delete_resume_profile(db: Session, profile_id: str) -> bool:
    profile = db.get(ResumeProfile, profile_id)
    if profile is None:
        return False
    db.delete(profile)
    db.commit()
    return True


def delete_resume_version(db: Session, version_id: str) -> bool:
    version = db.get(ResumeVersion, version_id)
    if version is None:
        return False
    db.delete(version)
    db.commit()
    return True


def list_resume_profiles(db: Session, limit: int = 20) -> list[ResumeProfile]:
    statement = (
        select(ResumeProfile)
        .options(selectinload(ResumeProfile.versions).selectinload(ResumeVersion.document))
        .order_by(desc(ResumeProfile.created_at))
        .limit(limit)
    )
    return list(db.scalars(statement))


def list_resume_versions(db: Session, limit: int = 50) -> list[ResumeVersion]:
    statement = (
        select(ResumeVersion)
        .options(selectinload(ResumeVersion.profile))
        .order_by(desc(ResumeVersion.created_at))
        .limit(limit)
    )
    return list(db.scalars(statement))


def create_job_source(
    db: Session,
    name: str,
    source_type: str,
    base_url: str | None = None,
    enabled: bool = True,
    config: dict[str, Any] | None = None,
) -> JobSource:
    source = JobSource(
        name=name,
        source_type=source_type,
        base_url=base_url or None,
        enabled=enabled,
        config=config or {},
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def create_job_subscription(
    db: Session,
    name: str,
    query: str,
    locations: list[str] | None = None,
    remote_policy: str | None = None,
    frequency: str = "daily",
) -> JobSubscription:
    subscription = JobSubscription(
        name=name,
        query=query,
        locations=locations or [],
        remote_policy=remote_policy or None,
        frequency=frequency,
        enabled=True,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def list_job_subscriptions(db: Session, limit: int = 20) -> list[JobSubscription]:
    statement = select(JobSubscription).order_by(desc(JobSubscription.created_at)).limit(limit)
    return list(db.scalars(statement))


def create_job_posting(
    db: Session,
    title: str,
    company: str | None = None,
    location: str | None = None,
    description: str | None = None,
    requirements: str | None = None,
    source_url: str | None = None,
    remote_policy: str | None = None,
    employment_type: str | None = None,
    document_id: str | None = None,
) -> JobPosting:
    posting = JobPosting(
        title=title,
        company=company or None,
        location=location or None,
        description=description or None,
        requirements=requirements or None,
        source_url=source_url or None,
        document_id=document_id or None,
        remote_policy=remote_policy or None,
        employment_type=employment_type or None,
        status="open",
        metadata_={"ingest_mode": "manual"},
    )
    db.add(posting)
    db.commit()
    db.refresh(posting)
    return posting


def list_job_postings(db: Session, limit: int = 30) -> list[JobPosting]:
    statement = select(JobPosting).order_by(desc(JobPosting.created_at)).limit(limit)
    return list(db.scalars(statement))


def create_application(
    db: Session,
    job_posting_id: str,
    resume_version_id: str | None = None,
    status: str = "interested",
    source: str | None = None,
    notes: str | None = None,
    next_action_at: datetime | None = None,
) -> Application:
    application = Application(
        job_posting_id=job_posting_id,
        resume_version_id=resume_version_id or None,
        status=status,
        source=source or None,
        notes=notes or None,
        next_action_at=next_action_at,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


def list_applications(db: Session, limit: int = 30) -> list[Application]:
    statement = (
        select(Application)
        .options(selectinload(Application.job_posting), selectinload(Application.resume_version))
        .order_by(desc(Application.created_at))
        .limit(limit)
    )
    return list(db.scalars(statement))


def create_career_goal(
    db: Session,
    title: str,
    target_role: str | None = None,
    target_date: datetime | None = None,
    description: str | None = None,
    success_criteria: list[str] | None = None,
) -> CareerGoal:
    goal = CareerGoal(
        title=title,
        target_role=target_role or None,
        target_date=target_date,
        description=description or None,
        success_criteria=success_criteria or [],
        status="active",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def create_learning_goal(
    db: Session,
    title: str,
    target_skill: str | None = None,
    target_date: datetime | None = None,
    description: str | None = None,
    success_criteria: list[str] | None = None,
) -> LearningGoal:
    goal = LearningGoal(
        title=title,
        target_skill=target_skill or None,
        target_date=target_date,
        description=description or None,
        success_criteria=success_criteria or [],
        status="active",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def list_career_goals(db: Session, limit: int = 20) -> list[CareerGoal]:
    statement = select(CareerGoal).order_by(desc(CareerGoal.created_at)).limit(limit)
    return list(db.scalars(statement))


def list_learning_goals(db: Session, limit: int = 20) -> list[LearningGoal]:
    statement = select(LearningGoal).order_by(desc(LearningGoal.created_at)).limit(limit)
    return list(db.scalars(statement))


def create_notification(
    db: Session,
    title: str,
    body: str,
    notification_type: str = "general",
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
) -> Notification:
    notification = Notification(
        title=title,
        body=body,
        notification_type=notification_type,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        status="unread",
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_notifications(db: Session, limit: int = 30) -> list[Notification]:
    statement = select(Notification).order_by(desc(Notification.created_at)).limit(limit)
    return list(db.scalars(statement))
