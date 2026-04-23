# WMS Quick Reference

## Core Flow

`Oracle WMS -> cx_Oracle extraction -> PostgreSQL bronze -> dbt-postgres -> PostgreSQL silver/gold -> FastAPI / Grafana / agents`

## Primary Components

- `docker-compose.yml`: local stack (PostgreSQL + Airflow + Grafana + Qdrant)
- `pipelines/`: extraction and orchestration
- `transform/dbt_wms/`: transformations and tests
- `app/api/`: serving layer
- `app/agents/`: AnalystAgent, ResearchAgent, ReporterAgent
- `docs/runbooks/`: future RAG corpus

## Domain Priorities

- preserve source traceability in bronze
- concentrate business logic in dbt intermediate and marts
- expose low-latency answers through PostgreSQL gold and API services
- use runbooks and docs as the semantic memory for the AI layer

## Non-Negotiables

- Local-first Docker Compose architecture
- No secrets committed to git (gitleaks pre-commit)
- Documented ADRs for major trade-offs
- Runbooks written as reusable operational memory
- WMS naming, never ShopAgent leftovers
