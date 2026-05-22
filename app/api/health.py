from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings


router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "phase": "phase_0_foundation",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "app": settings.public_summary(),
    }
