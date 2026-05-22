from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


settings = get_settings()

celery_app = Celery(
    "persona_graph",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_time_limit=60,
    task_soft_time_limit=45,
    result_expires=3600,
    timezone="Asia/Hong_Kong",
)
