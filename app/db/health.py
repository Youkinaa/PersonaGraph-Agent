from __future__ import annotations

from sqlalchemy import text

from app.db.session import SessionLocal


def check_database() -> dict[str, str]:
    try:
        with SessionLocal() as session:
            session.execute(text("select 1"))
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover - depends on local infrastructure
        return {"status": "error", "message": str(exc)}
