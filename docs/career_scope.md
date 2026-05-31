# Career Scope Consolidation

PersonaGraph Career Agent narrows the project around job search and career
planning while keeping the reusable engineering foundation.

## Kept From The Original Platform

- FastAPI + Jinja2 + HTMX workbench.
- PostgreSQL as the source of truth.
- Redis + Celery for background work.
- Milvus for vector retrieval.
- Elasticsearch for keyword/BM25 retrieval.
- Neo4j for graph retrieval.
- LangGraph and LangChain for workflow orchestration.
- Dynamic SKILL.md runtime.
- Memory lifecycle.

## Removed As Standalone Product Areas

- Travel planning assistant.
- Generic GitHub repository analysis assistant.
- Generic research report assistant as a top-level product.

## Migrated Into Career Workflows

- GitHub/project analysis becomes project evidence ingestion for resumes.
- Technical research becomes company, role, and technology-stack research.
- Proactive notifications become job alerts, application reminders, interview
  prep reminders, and weekly career reviews.
- GraphRAG becomes a career graph for skills, requirements, projects, jobs,
  companies, applications, milestones, and learning resources.

## Job Discovery Strategy

The system should not depend on private or login-only recruitment platforms.
The first adapters should be:

- SerpApi Google Jobs adapter.
- Manual JD import adapter.
- Company career page adapter for public company career pages.

Avoid:

- Simulated BOSS Zhipin login.
- Anti-bot bypass.
- Automated messaging to recruiters.
- Any workflow that depends on private user sessions from recruitment sites.
