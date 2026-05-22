from __future__ import annotations

from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.domains.tasks.service import mark_task_failed, mark_task_running, mark_task_succeeded
from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.ping")
def ping_task(task_run_id: str, message: str = "pong") -> dict:
    with SessionLocal() as db:
        try:
            mark_task_running(db, task_run_id)
            result = {
                "message": message,
                "worker_checked_at": datetime.now(timezone.utc).isoformat(),
            }
            mark_task_succeeded(db, task_run_id, result)
            return result
        except Exception as exc:
            mark_task_failed(db, task_run_id, str(exc))
            raise
