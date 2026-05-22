from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from app.core.config import Settings, get_settings


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
            "phase": "Phase 0",
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
