# CLAUDE.md

This file provides guidance when working with code in this repository.

## Project Overview

WMS Data Platform is a modern data engineering portfolio project built on top of Oracle WMS. It covers the full data engineering cycle: batch extraction, medallion architecture (bronze/silver/gold schemas on PostgreSQL), dbt transformations, Airflow orchestration, geographic enrichment via public APIs, and a conversational AI layer with autonomous agents.

---

## Commands

```bash
# Local environment
make dev          # docker-compose up -d (PostgreSQL + Airflow + Grafana)
make test         # pytest tests/
make test-unit    # pytest tests/unit/
make lint         # pre-commit run --all-files (black, flake8, isort, gitleaks)

# dbt
dbt run --project-dir transform/dbt_wms
dbt test --project-dir transform/dbt_wms
dbt compile --project-dir transform/dbt_wms
```

Pre-commit hooks: `black`, `flake8`, `isort`, `gitleaks`.

---

## Architecture

### Data Flow

```
Oracle WMS
  └─[batch]─► Airflow → Python extractor (cx_Oracle) ──► PostgreSQL bronze
                                                                │
              ViaCEP + IBGE + Open-Meteo                        │
                enrichment scripts ─────────────────────────────►│
                                                                │
                                               dbt-postgres → PostgreSQL silver
                                               dbt-postgres → PostgreSQL gold
                                                                │
                                         ┌──────────────────────┤
                                    AI Agents               Grafana
                               AnalystAgent (SQL)           4 Dashboards
                               ResearchAgent (RAG)
                               ReporterAgent (synthesis)
                                         │
                                    FastAPI
                                         │
                                  React + Vite
```

### Layer-by-Layer Summary

| Layer | Location | Technology |
|---|---|---|
| Orchestration | `pipelines/dags/` | Apache Airflow (local Docker, 7 DAGs) |
| Batch extraction | `pipelines/extraction/` | Python + cx_Oracle, checkpoint in PostgreSQL |
| Enrichment | `pipelines/enrichment/` | Python scripts, APIs: ViaCEP/IBGE/Open-Meteo/ANTT |
| Data Lake | PostgreSQL schemas | bronze / silver / gold medallion |
| Transformations | `transform/dbt_wms/` | dbt Core + dbt-postgres |
| Serving | PostgreSQL gold schema | 8 analytical marts |
| AI Agents | `app/agents/` | LangChain/CrewAI, Claude via Anthropic API, Qdrant RAG |
| API | `app/api/` | FastAPI |
| Frontend | `web/` | React + Vite |

### Key Architectural Decisions

- **Medallion on PostgreSQL** (ADR-001): bronze/silver/gold schemas on a single Postgres instance; simple, portable, no cloud dependency.
- **Batch extraction over CDC** (ADR-002): cx_Oracle incremental extraction with checkpoint; reliable and self-contained.
- **dbt-postgres for transform and serving** (ADR-003): dbt models compile to PostgreSQL; same engine for transform and consumption.

### dbt Marts

Eight analytical models in `transform/dbt_wms/models/marts/`:
- `mart_picking_performance` — operator/shift productivity
- `mart_inventory_health` — turnover, coverage, stockout risk
- `mart_order_sla` — cycle time, deadline adherence
- `mart_operator_productivity` — ranking with complexity context
- `mart_stockout_risk` — SKU-level stockout projection
- `mart_geo_performance` — SLA by state/city (choropleth)
- `mart_geo_inventory` — inventory coverage by region
- `mart_weather_impact` — delay × weather correlation

### CI/CD (GitHub Actions)

| Workflow | Trigger |
|---|---|
| `ci.yml` | PR — lint, tests, dbt compile |
| `dbt-run.yml` | Scheduled daily dbt run + test |
| `security-scan.yml` | bandit, trivy, gitleaks |

Branch strategy: `feature/*` → `dev` → `main`.

---

## Tech Stack

- **Language**: Python 3.11+
- **Orchestration**: Apache Airflow (local Docker)
- **Database**: PostgreSQL 15 (bronze / silver / gold schemas)
- **Transform**: dbt Core + dbt-postgres
- **Enrichment**: ViaCEP, IBGE, Open-Meteo, ANTT (public APIs)
- **AI Agents**: LangChain / CrewAI, Claude via Anthropic API
- **Vector store**: Qdrant (local Docker)
- **API**: FastAPI
- **Frontend**: React + Vite
- **Dashboards**: Grafana (local Docker, port 3000)
- **Observability**: LangFuse, DeepEval
- **Local dev**: Docker Compose, Pre-commit
