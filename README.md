# PersonaGraph Career Agent

PersonaGraph Career Agent is a career-focused AI agent platform for job search,
resume/JD matching, job monitoring, interview preparation, and technical
learning roadmaps.

The project keeps the original platform idea, but narrows the business scope to
career workflows. The reusable capability pool is still the same: memory,
document retrieval, graph retrieval, dynamic skills, background jobs, and
workflow orchestration. GitHub analysis and travel planning are no longer
standalone products; GitHub/project material becomes career evidence, and travel
planning is removed.

## Product Scope

Core workflows:

- Resume and project knowledge base.
- JD analysis and resume-JD matching.
- Job subscription, discovery, scoring, and notification.
- Application tracking and weekly review.
- Interview preparation from JD requirements and project evidence.
- Career planning and technical learning roadmaps.

Non-goals:

- No generic chatbot as the main product.
- No BOSS Zhipin login automation or anti-bot bypass.
- No standalone GitHub repository analysis assistant.
- No travel planning assistant.

## Architecture

```text
FastAPI + Jinja2 + HTMX Workbench
  -> API / partial routes
  -> Intent Router / LangGraph workflows
  -> Capability Pool
      -> Career memory
      -> Resume/JD document RAG
      -> Job discovery adapters
      -> Career graph retrieval
      -> Dynamic SKILL.md runtime
      -> Notification service
      -> Task manager
  -> Storage / Index Layer
      -> PostgreSQL
      -> Redis + Celery
      -> Milvus
      -> Elasticsearch
      -> Neo4j
```

## Phase 0

Implemented:

- FastAPI application shell.
- Jinja2 + HTMX workspace page.
- `.env`-driven settings with secret-safe summaries.
- `/health` endpoint.
- Request logging with request ids.
- Central error handlers.

## Phase 1

Implemented:

- PostgreSQL connection through SQLAlchemy.
- Alembic migration for core platform tables.
- Redis connectivity check.
- Celery app and a minimal `tasks.ping` worker task.
- `task_runs` lifecycle: `queued -> running -> succeeded / failed`.
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

Why these still fit the career-focused project:

- `documents`, `document_sections`, and `document_chunks` will store resumes,
  JDs, project docs, company notes, and interview notes.
- `workflow_runs` and `messages` will store LangGraph career workflow runs.
- `task_runs` will track document parsing, indexing, job scans, notifications,
  and memory consolidation.
- `users` stays schema-only for now; authentication is deferred.

Still not implemented yet:

- Career-specific tables such as resumes, job postings, subscriptions,
  applications, goals, notifications, and milestones.
- Milvus / Elasticsearch / Neo4j indexing.
- LangGraph workflows.
- Memory lifecycle.
- Skill runtime.

## Phase 2

Implemented:

- Career domain tables for resumes, jobs, applications, goals, notifications,
  and proactive events.
- Alembic migration `0002_career_domain`.
- Career domain service layer.
- JSON API under `/api/career`.
- Server-rendered pages for:
  - `/resumes`
  - `/jobs`
  - `/applications`
  - `/goals`
  - `/notifications`

Current simplifications:

- Resume versions and JDs can be entered manually; file upload starts in the
  next phase.
- Job subscriptions are stored but not scheduled yet.
- Notifications can be created manually; proactive generation starts later.
- Career goals and learning goals are stored but not planned by LangGraph yet.

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

The existing infrastructure compose file lives outside this repository:

```text
D:\docker-data\compose\docker-compose.yml
```

Start it with:

```powershell
docker compose -f D:\docker-data\compose\docker-compose.yml up -d
```

Expected containers:

- `postgres`: main business database.
- `milvus-standalone`: vector search.
- `milvus-etcd`: Milvus metadata dependency.
- `milvus-minio`: Milvus object storage dependency.
- `es`: Elasticsearch keyword/BM25 search.
- `neo4j`: career graph index.
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

## Configuration

Copy `.env.example` to `.env` when starting from a clean machine. Keep real API
keys only in `.env`.

Required variables:

- `LLM_API_KEY`
- `LLM_MODEL_ID`
- `LLM_BASE_URL`
- `SERPAPI_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `MILVUS_URI`
- `ELASTICSEARCH_URL`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

## Verification

Run tests:

```powershell
python -m pytest -q
```

Expected:

```text
2 passed
```

Check migration state:

```powershell
python -m alembic current
```

Expected:

```text
0002_career_domain (head)
```

Verify dependencies:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/dependencies
```

Expected:

- `checks.database.status`: `ok`
- `checks.redis.status`: `ok`

Verify Celery task flow:

```powershell
$task = Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/tasks/ping
Start-Sleep -Seconds 2
Invoke-RestMethod http://127.0.0.1:8000/api/tasks/$($task.id)
```

Expected:

- `task_name`: `celery_ping`
- `status`: `succeeded`
- `result.message`: `pong`

Verify career pages:

```text
http://127.0.0.1:8000/resumes
http://127.0.0.1:8000/jobs
http://127.0.0.1:8000/applications
http://127.0.0.1:8000/goals
http://127.0.0.1:8000/notifications
```

Verify career APIs:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/career/resumes
Invoke-RestMethod http://127.0.0.1:8000/api/career/jobs
Invoke-RestMethod http://127.0.0.1:8000/api/career/applications
Invoke-RestMethod http://127.0.0.1:8000/api/career/goals
Invoke-RestMethod http://127.0.0.1:8000/api/career/notifications
```

## Next Phase

Phase 3 will add resume/JD/project document upload, parsing status, parent
sections, child chunks, and Celery-backed parsing tasks.
