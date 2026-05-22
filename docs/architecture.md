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

## Phase 0 Runtime

```text
Browser
  -> FastAPI page routes
  -> Jinja2 templates
  -> HTMX partial endpoints
```

The health endpoint intentionally does not connect to infrastructure yet. Phase
1 will add real dependency checks after database and task state are introduced.
