# PersonaGraph Career Agent Stages

This project is built in small, verifiable phases. Each phase should keep the
system runnable and document what is real, what is a placeholder, and what comes
next.

## Phase 0: Foundation

Implemented:

- FastAPI application entrypoint.
- Jinja2 server-rendered workspace.
- HTMX-ready partial refresh.
- Pydantic settings loaded from `.env`.
- Secret-safe health check.
- Request id middleware and basic request logging.
- Central exception handlers.

## Phase 1: Career Platform State

Implemented:

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

Why this phase remains valid after the career-focused scope change:

- Resume, JD, project, company, and interview materials are still documents.
- Parent sections and child chunks are still the foundation for career RAG.
- Workflow runs will track LangGraph career workflows.
- Task runs will track parsing, indexing, job scans, and notifications.

Current placeholders:

- Celery only runs a simple ping task.
- Document tables exist, but upload and parsing are not implemented yet.
- Career-specific tables are not implemented yet.
- `users` is schema-only; authentication is intentionally deferred.

## Phase 2: Career Domain Schema

Planned:

- `resume_profiles`
- `resume_versions`
- `job_sources`
- `job_subscriptions`
- `job_fetch_runs`
- `job_postings`
- `job_scores`
- `applications`
- `career_goals`
- `learning_goals`
- `notifications`
- `proactive_events`

User-facing pages:

- `/resumes`
- `/jobs`
- `/applications`
- `/goals`
- `/notifications`

## Phase 3: Resume / JD Document Ingestion

Planned:

- Resume upload.
- JD paste/import.
- Project evidence document upload.
- File persistence.
- Document parse state transitions.
- Parent section splitting.
- Child chunk splitting.
- Celery-backed parsing task.

## Phase 4: Hybrid RAG

Planned:

- Milvus collection for child chunk embeddings.
- Elasticsearch index for BM25/full-text retrieval.
- RRF fusion.
- Parent fetch from PostgreSQL.
- Evidence Pack for resume/JD matching.

## Phase 5: Career GraphRAG

Planned:

- Skill and requirement extraction.
- Project-skill and job-skill graph construction.
- Neo4j graph expansion.
- Skill gap paths.
- Learning prerequisite paths.

## Phase 6: Job Discovery And Notifications

Planned:

- SerpApi Google Jobs adapter.
- Manual JD import adapter.
- Company career page adapter.
- Job deduplication.
- Job scoring against resume, memory, and career graph.
- Notification center.
- Celery Beat scheduled scans.

## Phase 7: Planning Workflows

Planned:

- Career planning skill.
- Learning roadmap skill.
- Interview preparation skill.
- Weekly career review skill.
- Milestone generation and review.
