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

Implemented in this phase:

- PostgreSQL connection.
- SQLAlchemy models.
- Alembic migrations.
- Redis connectivity check.
- Minimal Celery worker.
- `workflow_runs`, `task_runs`, `messages`, `documents`, `document_sections`,
  and `document_chunks` base tables.
- `/health/dependencies` endpoint.
- `tasks.ping` background task.
- HTMX task controls on the workspace page.

Current placeholders:

- Celery only runs a simple ping task.
- Document tables exist, but upload and parsing are not implemented yet.
- `users` is schema-only; authentication is intentionally deferred.

## Phase 2: Document Ingestion

Planned next:

- Upload page and API.
- File persistence.
- Document parse state transitions.
- Parent section splitting.
- Child chunk splitting.
- Celery-backed parsing task.
