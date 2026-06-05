from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import TaskRun


def create_task_run(db: Session, task_name: str, payload: dict[str, Any] | None = None) -> TaskRun:
    task_run = TaskRun(task_name=task_name, status="queued", payload=payload or {})
    db.add(task_run)
    db.commit()
    db.refresh(task_run)
    return task_run


def attach_celery_task(db: Session, task_run_id: str, celery_task_id: str) -> TaskRun | None:
    task_run = db.get(TaskRun, task_run_id)
    if task_run is None:
        return None
    task_run.celery_task_id = celery_task_id
    db.commit()
    db.refresh(task_run)
    return task_run


def mark_task_running(db: Session, task_run_id: str) -> TaskRun | None:
    task_run = db.get(TaskRun, task_run_id)
    if task_run is None:
        return None
    task_run.status = "running"
    task_run.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task_run)
    return task_run


def mark_task_succeeded(db: Session, task_run_id: str, result: dict[str, Any]) -> TaskRun | None:
    task_run = db.get(TaskRun, task_run_id)
    if task_run is None:
        return None
    task_run.status = "succeeded"
    task_run.result = result
    task_run.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task_run)
    return task_run


def mark_task_failed(db: Session, task_run_id: str, message: str) -> TaskRun | None:
    task_run = db.get(TaskRun, task_run_id)
    if task_run is None:
        return None
    task_run.status = "failed"
    task_run.error_message = message
    task_run.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task_run)
    return task_run


def get_task_run(db: Session, task_run_id: str) -> TaskRun | None:
    return db.get(TaskRun, task_run_id)


def list_recent_task_runs(db: Session, limit: int = 8) -> list[TaskRun]:
    statement = select(TaskRun).order_by(desc(TaskRun.created_at)).limit(limit)
    return list(db.scalars(statement))


def list_task_runs_by_payload(db: Session, payload_key: str, payload_value: str, limit: int = 20) -> list[TaskRun]:
    statement = (
        select(TaskRun)
        .where(TaskRun.payload[payload_key].astext == payload_value)
        .order_by(desc(TaskRun.created_at))
        .limit(limit)
    )
    return list(db.scalars(statement))
