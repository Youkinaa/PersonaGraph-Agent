from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.redis import check_redis
from app.db.health import check_database


router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "phase": settings.app_phase,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "app": settings.public_summary(),
    }


@router.get("/health/dependencies")
def dependency_health(settings: Settings = Depends(get_settings)) -> dict:
    checks = {
        "database": check_database(),
        "redis": check_redis(),
    }
    status_value = "ok" if all(item["status"] == "ok" for item in checks.values()) else "degraded"
    return {
        "status": status_value,
        "phase": settings.app_phase,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
