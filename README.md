# PersonaGraph Agent

PersonaGraph Agent is a personal workflow agent platform built around long-term
memory, dynamic skills, hybrid retrieval, graph retrieval, and workflow
orchestration.

The project is implemented in small phases so every slice can be run, tested,
and explained.

## Phase 0

Current implementation:

- FastAPI application shell.
- Jinja2 + HTMX workspace page.
- `.env`-driven settings with secret-safe summaries.
- `/health` endpoint.
- Request logging with request ids.
- Central error handlers.

## Phase 1

Current implementation:

- PostgreSQL connection through SQLAlchemy.
- Alembic migration for core platform tables.
- Redis connectivity check.
- Celery app and a minimal `tasks.ping` worker task.
- `task_runs` status lifecycle: `queued -> running -> succeeded / failed`.
- API endpoints for dependency health and task status.
- HTMX controls for dependency checks and Celery ping tasks.

Core tables created in Phase 1:

- `users`
- `documents`
- `document_sections`
- `document_chunks`
- `workflow_runs`
- `messages`
- `task_runs`

Still not implemented yet:

- Milvus / Elasticsearch / Neo4j indexing.
- LangGraph workflows.
- Memory lifecycle.
- Skill runtime.

## Local Run

Create a virtual environment, install dependencies, then start the app:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/health
http://127.0.0.1:8000/health/dependencies
```

Run the Celery worker in a second terminal. On Windows, use the `solo` pool:

```powershell
python -m celery -A app.workers.celery_app worker --pool=solo --loglevel=info
```

Apply database migrations:

```powershell
python -m alembic upgrade head
```

Trigger a background ping task:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/tasks/ping
```

## Docker Infrastructure

Phase 0 does not connect to PostgreSQL, Redis, Milvus, Elasticsearch, or Neo4j
yet. The application only reads their connection settings from `.env`.

Your current infrastructure compose file lives outside this repository:

```text
D:\docker-data\compose\docker-compose.yml
```

Start the existing infrastructure stack:

```powershell
docker compose -f D:\docker-data\compose\docker-compose.yml up -d
```

Expected containers for the confirmed architecture:

- `postgres`: main business database.
- `milvus-standalone`: vector search.
- `milvus-etcd`: Milvus metadata dependency.
- `milvus-minio`: Milvus object storage dependency.
- `es`: Elasticsearch keyword/BM25 search.
- `neo4j`: graph index.
- `milvus-attu`: optional Milvus UI.

Redis is currently managed separately under:

```text
D:\Redis
```

If Redis is not already running on port `6379`, start it from that directory:

```powershell
cd D:\Redis
.\redis-server.exe
```

Check running containers:

```powershell
docker ps
```

Check Redis connectivity:

```powershell
Test-NetConnection 127.0.0.1 -Port 6379
```

## Configuration

Copy `.env.example` to `.env` when starting from a clean machine. Keep real API
keys only in `.env`.

Existing keys used in Phase 0:

- `LLM_API_KEY`
- `LLM_MODEL_ID`
- `LLM_BASE_URL`
- `SERPAPI_API_KEY`

Infrastructure settings are already modeled but not connected until Phase 1.

Required infrastructure variables for later phases:

- `DATABASE_URL`
- `REDIS_URL`
- `MILVUS_URI`
- `ELASTICSEARCH_URL`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

## Verification

Phase 1 verifies the application foundation, database state, Redis connectivity,
and one Celery background task. It still does not verify the full RAG stack.

Run tests:

```powershell
python -m pytest -q
```

Expected result:

```text
2 passed
```

Verify routes through the running FastAPI app:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected fields:

- `status`: `ok`
- `phase`: `phase_1_task_state`
- `app.has_llm_api_key`: whether `.env` contains an LLM key.
- `app.has_serpapi_api_key`: whether `.env` contains a SerpAPI key.

Verify dependencies:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/dependencies
```

Expected:

- `checks.database.status`: `ok`
- `checks.redis.status`: `ok`

Manual browser checks:

- `http://127.0.0.1:8000` renders the workspace page.
- `http://127.0.0.1:8000/health` returns JSON.
- The `Refresh` button on the workspace page updates the status panel through
  HTMX.
- The `Check` button validates PostgreSQL and Redis.
- The `Enqueue Ping` button creates a task row and lets the Celery worker mark
  it as succeeded.

Phase 2 will add document upload, parsing status, parent sections, and child
chunks.
