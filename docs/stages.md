# PersonaGraph Agent Stages

This project is built in small, verifiable phases. Each phase should keep the
system runnable and document what is real, what is a placeholder, and what comes
next.

## Phase 0: Foundation

Implemented in this phase:

- FastAPI application entrypoint.
- Jinja2 server-rendered workspace.
- HTMX-ready partial refresh.
- Pydantic settings loaded from `.env`.
- Secret-safe health check.
- Request id middleware and basic request logging.
- Central exception handlers.

Current placeholders:

- No database connection yet.
- No Redis or Celery task execution yet.
- No LangGraph workflows yet.
- No RAG indexing yet.

## Phase 1: Database And Task State

Planned next:

- PostgreSQL connection.
- SQLAlchemy models.
- Alembic migrations.
- Redis connectivity check.
- Minimal Celery worker.
- `workflow_runs`, `task_runs`, `messages`, `documents` base tables.
