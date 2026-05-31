from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.redis import check_redis
from app.db.health import check_database
from app.db.session import get_db
from app.domains.tasks.service import (
    attach_celery_task,
    create_task_run,
    get_task_run,
    list_recent_task_runs,
    mark_task_failed,
)
from app.workers.tasks import ping_task


templates = Jinja2Templates(directory=str(get_settings().templates_dir))
router = APIRouter(include_in_schema=False)


@router.get("/")
async def index(request: Request, settings: Settings = Depends(get_settings)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "settings": settings,
            "phase": "Phase 2",
        },
    )


@router.get("/partials/phase-status")
async def phase_status(request: Request, settings: Settings = Depends(get_settings)):
    return templates.TemplateResponse(
        request=request,
        name="partials/phase_status.html",
        context={
            "request": request,
            "settings": settings,
            "summary": settings.public_summary(),
        },
    )


@router.get("/partials/dependency-status")
def dependency_status(request: Request):
    checks = {
        "database": check_database(),
        "redis": check_redis(),
    }
    return templates.TemplateResponse(
        request=request,
        name="partials/dependency_status.html",
        context={
            "request": request,
            "checks": checks,
        },
    )


@router.post("/partials/tasks/ping")
def enqueue_ping_task_card(request: Request, db: Session = Depends(get_db)):
    task_run = create_task_run(db, task_name="celery_ping", payload={"message": "pong"})
    try:
        async_result = ping_task.delay(task_run.id, "pong")
    except Exception as exc:
        task_run = mark_task_failed(db, task_run.id, f"Failed to enqueue task: {exc}") or task_run
    else:
        task_run = attach_celery_task(db, task_run.id, async_result.id) or task_run

    return templates.TemplateResponse(
        request=request,
        name="partials/task_run.html",
        context={
            "request": request,
            "task_run": task_run,
        },
    )


@router.get("/partials/tasks/recent")
def recent_tasks(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="partials/recent_tasks.html",
        context={
            "request": request,
            "task_runs": list_recent_task_runs(db),
        },
    )


@router.get("/partials/tasks/{task_run_id}")
def task_run_card(request: Request, task_run_id: str, db: Session = Depends(get_db)):
    task_run = get_task_run(db, task_run_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/task_run.html",
        context={
            "request": request,
            "task_run": task_run,
        },
    )
