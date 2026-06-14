from __future__ import annotations

from sqlalchemy.orm import Session

from app.domains.tasks.service import attach_celery_task, create_task_run
from app.domains.rag.service import list_stale_index_documents
from app.workers.tasks import index_document_task, reindex_document_task


def enqueue_index_document(db: Session, document_id: str):
    task_run = create_task_run(db, task_name="document_index", payload={"document_id": document_id})
    async_result = index_document_task.delay(task_run.id, document_id)
    return attach_celery_task(db, task_run.id, async_result.id) or task_run


def enqueue_reindex_document(db: Session, document_id: str):
    task_run = create_task_run(db, task_name="document_reindex", payload={"document_id": document_id})
    async_result = reindex_document_task.delay(task_run.id, document_id)
    return attach_celery_task(db, task_run.id, async_result.id) or task_run


def enqueue_reindex_stale_documents(db: Session, limit: int = 20) -> dict:
    documents = list_stale_index_documents(db, limit=limit)
    task_runs = [enqueue_reindex_document(db, document.id) for document in documents]
    return {
        "queued": len(task_runs),
        "document_ids": [document.id for document in documents],
        "task_run_ids": [task_run.id for task_run in task_runs],
    }
