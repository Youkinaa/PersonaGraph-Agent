from __future__ import annotations

from redis import Redis

from app.core.config import get_settings


def get_redis_client() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


def check_redis() -> dict[str, str]:
    try:
        client = get_redis_client()
        client.ping()
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover - depends on local infrastructure
        return {"status": "error", "message": str(exc)}
