from __future__ import annotations

from sqlalchemy.orm import Session

from app.domains.career import service as career_service


def normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def link_document_to_career(
    db: Session,
    document_id: str,
    doc_type: str,
    title: str,
    resume_profile_id: str | None = None,
    resume_profile_title: str | None = None,
    resume_target_role: str | None = None,
    resume_version_label: str = "uploaded",
    company: str | None = None,
    location: str | None = None,
    source_url: str | None = None,
) -> None:
    normalized_doc_type = normalize_optional(doc_type) or "generic"
    profile_id = normalize_optional(resume_profile_id)

    if normalized_doc_type == "resume":
        if profile_id is None:
            profile = career_service.create_resume_profile(
                db,
                title=normalize_optional(resume_profile_title) or title,
                target_role=normalize_optional(resume_target_role),
                summary=None,
            )
            profile_id = profile.id

        career_service.create_resume_version(
            db,
            profile_id=profile_id,
            version_label=normalize_optional(resume_version_label) or "uploaded",
            document_id=document_id,
            source_type="document",
            is_primary=False,
        )

    if normalized_doc_type == "jd":
        career_service.create_job_posting(
            db,
            title=title,
            company=normalize_optional(company),
            location=normalize_optional(location),
            source_url=normalize_optional(source_url),
            document_id=document_id,
        )
