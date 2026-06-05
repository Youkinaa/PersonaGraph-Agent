from __future__ import annotations

from sqlalchemy.orm import Session

from app.domains.tasks.service import attach_celery_task, create_task_run
from app.workers.tasks import parse_document_task


def enqueue_parse_document(db: Session, document_id: str):
    task_run = create_task_run(db, task_name="document_parse", payload={"document_id": document_id})
    async_result = parse_document_task.delay(task_run.id, document_id)
    return attach_celery_task(db, task_run.id, async_result.id) or task_run
