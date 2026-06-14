# PersonaGraph Career Agent Stages

This project is built in small, verifiable phases. Each phase should keep the
system runnable and document what is real, what is a placeholder, and what comes
next.

Detailed current planning is maintained in `docs/project_roadmap.md`. This file
keeps the historical stage summary.

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

Implemented:

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

Current placeholders:

- Manual resume and JD entry only; file upload is not implemented yet.
- Job subscriptions are not scheduled yet.
- Notifications are manually created; proactive generation starts later.
- Career and learning goals are stored, not planned by an Agent yet.

## Phase 3: Resume / JD Document Ingestion

Implemented:

- Resume upload.
- JD paste/import.
- Project evidence document upload.
- File persistence.
- Document parse state transitions.
- Parent section splitting.
- Child chunk splitting.
- Celery-backed parsing task.
- Automatic resume profile and version creation for resume documents.
- Existing resume document attachment to resume versions.
- Document deletion with local file, section, and chunk cleanup.
- Resume profile and version deletion without deleting raw documents.
- Phase design issue tracking in `docs/phase_review_log.md`.

Current placeholders:

- No Milvus embeddings yet.
- No Elasticsearch BM25 indexing yet.
- No Neo4j entity extraction yet.
- PDF parsing is text-only and not layout-aware.
- No external index cleanup yet because Milvus, Elasticsearch, and Neo4j
  indexing are intentionally deferred.

## Phase 4: Hybrid RAG

Implemented:

- Config-driven global phase label and phase slug.
- Elasticsearch index adapter for chunk BM25/full-text retrieval.
- Milvus collection adapter for child chunk vector retrieval.
- `text-embedding-v4` embedding provider through the OpenAI-compatible API.
- Deterministic local hashing embedding as a fallback/test implementation.
- Per-document indexing task and `/documents` page index action.
- `/api/rag/search` endpoint.
- `/rag` page for fused Evidence Pack inspection.
- RRF fusion.
- Parent fetch from PostgreSQL.
- Local PostgreSQL keyword fallback when ES or Milvus is unavailable.
- Evidence Pack for downstream resume/JD matching.

Current placeholders:

- Embedding quality now depends on `text-embedding-v4`; local hashing is only a
  fallback path when the embedding API is unavailable.
- External index cleanup on document delete is not implemented yet.
- Reranking is not implemented yet.
- Graph expansion is deferred to Phase 5.

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
