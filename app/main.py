from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.career import router as career_router
from app.api.health import router as health_router
from app.api.tasks import router as task_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging
from app.pages.career import router as career_page_router
from app.pages.router import router as page_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
    app.include_router(career_router)
    app.include_router(health_router)
    app.include_router(task_router)
    app.include_router(career_page_router)
    app.include_router(page_router)

    return app


app = create_app()
