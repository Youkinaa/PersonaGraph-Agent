# PersonaGraph Agent Architecture

PersonaGraph Agent is a personal workflow agent platform. It exposes reusable
capabilities such as memory, document retrieval, graph retrieval, tools, skills,
and workflow orchestration, then composes them through task-specific workflows.

## Confirmed Stack

- UI: FastAPI, Jinja2, HTMX.
- Agent runtime: LangGraph and LangChain.
- Main store: PostgreSQL.
- Vector search: Milvus.
- Keyword search: Elasticsearch.
- Graph index: Neo4j.
- Cache and task broker: Redis.
- Background jobs: Celery.

## Phase 1 Runtime

```text
Browser
  -> FastAPI page routes
  -> Jinja2 templates
  -> HTMX partial endpoints
  -> PostgreSQL for state
  -> Redis broker
  -> Celery worker
```

PostgreSQL is the source of truth for platform state. Redis is used as the
Celery broker and result backend. Celery is reserved for work that should live
outside the request lifecycle, such as document parsing, indexing, memory
consolidation, and proactive jobs in later phases.
