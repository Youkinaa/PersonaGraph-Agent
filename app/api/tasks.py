from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domains.tasks.service import attach_celery_task, create_task_run, get_task_run, mark_task_failed
from app.workers.tasks import ping_task


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskRunResponse(BaseModel):
    id: str
    task_name: str
    status: str
    celery_task_id: str | None
    payload: dict
    result: dict | None
    error_message: str | None


def serialize_task_run(task_run) -> TaskRunResponse:
    return TaskRunResponse(
        id=task_run.id,
        task_name=task_run.task_name,
        status=task_run.status,
        celery_task_id=task_run.celery_task_id,
        payload=task_run.payload,
        result=task_run.result,
        error_message=task_run.error_message,
    )


@router.post("/ping", response_model=TaskRunResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_ping_task(db: Session = Depends(get_db)) -> TaskRunResponse:
    task_run = create_task_run(db, task_name="celery_ping", payload={"message": "pong"})
    try:
        async_result = ping_task.delay(task_run.id, "pong")
    except Exception as exc:
        task_run = mark_task_failed(db, task_run.id, f"Failed to enqueue task: {exc}") or task_run
    else:
        task_run = attach_celery_task(db, task_run.id, async_result.id) or task_run
    return serialize_task_run(task_run)


@router.get("/{task_run_id}", response_model=TaskRunResponse)
def read_task_run(task_run_id: str, db: Session = Depends(get_db)) -> TaskRunResponse:
    task_run = get_task_run(db, task_run_id)
    if task_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task run not found.")
    return serialize_task_run(task_run)
