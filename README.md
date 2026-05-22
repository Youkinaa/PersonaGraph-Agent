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

Not implemented yet:

- PostgreSQL models and migrations.
- Redis / Celery runtime.
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

Phase 0 verifies the application foundation, not the full RAG stack.

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
- `phase`: `phase_0_foundation`
- `app.has_llm_api_key`: whether `.env` contains an LLM key.
- `app.has_serpapi_api_key`: whether `.env` contains a SerpAPI key.

Manual browser checks:

- `http://127.0.0.1:8000` renders the workspace page.
- `http://127.0.0.1:8000/health` returns JSON.
- The `Refresh` button on the workspace page updates the status panel through
  HTMX.

Phase 1 will add real checks for PostgreSQL, Redis, and Celery.
