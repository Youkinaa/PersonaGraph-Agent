# PersonaGraph Career Agent Architecture

PersonaGraph Career Agent is a career-focused agent platform. It composes
career memory, resume/JD document retrieval, job discovery adapters, career
graph retrieval, tools, skills, and workflow orchestration into job-search
workflows.

## Scope Shift

Previous scope:

- Generic personal workflow platform.
- Job search assistant.
- GitHub analysis assistant.
- Travel planning assistant.

Current scope:

- Career assistant as the main product.
- GitHub/project data only as resume and project evidence.
- Travel planning removed.
- Technical research reframed as company, role, and technology-stack research
  for career planning.

## Confirmed Stack

- UI: FastAPI, Jinja2, HTMX.
- Agent runtime: LangGraph and LangChain.
- Main store: PostgreSQL.
- Vector search: Milvus.
- Keyword search: Elasticsearch.
- Graph index: Neo4j.
- Cache and task broker: Redis.
- Background jobs: Celery.
- Later scheduler: Celery Beat.

## Runtime Shape

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
outside the request lifecycle, such as document parsing, indexing, job scanning,
notification generation, memory consolidation, and proactive career reviews.

## Capability Pool

```text
Career Memory Service
Resume / JD Document RAG
Job Discovery Service
Career Graph Retrieval
Skill Runtime
Notification Service
Task Manager
```

## Career Graph Direction

Neo4j will model career relationships rather than generic topic graphs:

```text
Candidate
Resume
Project
Skill
Technology
JobPosting
Company
Requirement
Application
LearningResource
Milestone
Memory
```

Example relationships:

```text
Candidate -[:HAS_SKILL]-> Skill
Project -[:DEMONSTRATES]-> Skill
JobPosting -[:REQUIRES]-> Skill
JobPosting -[:POSTED_BY]-> Company
Application -[:TARGETS]-> JobPosting
Skill -[:PREREQUISITE_OF]-> Skill
LearningResource -[:TEACHES]-> Skill
```

This graph will support JD evidence matching, skill-gap analysis, personalized
learning roadmaps, application review, and proactive job recommendations.
