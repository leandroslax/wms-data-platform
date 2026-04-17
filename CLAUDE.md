# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WMS Data Platform is a modern data engineering portfolio project built on top of Oracle WMS. It covers the full data engineering cycle: real-time CDC, medallion architecture on S3 with Apache Iceberg, dbt on Glue, Airflow orchestration, geographic enrichment, Redshift Serverless warehouse, and a conversational AI layer with autonomous agents.

> **Note:** As of April 2026, only the architecture documentation exists (`docs/architecture.md`). The full repository structure below represents the planned implementation.

---

## Planned Commands

Once implemented, development will use:

```bash
# Local environment
make dev          # docker-compose up (Oracle XE + Airflow mock)
make test         # pytest tests/
make test-unit    # pytest tests/unit/
make lint         # pre-commit run --all-files (black, flake8, isort, checkov, gitleaks)

# dbt
dbt run --project-dir transform/dbt_wms
dbt test --project-dir transform/dbt_wms
dbt compile --project-dir transform/dbt_wms

# Terraform
cd infra/terraform/envs/dev && terraform init && terraform plan
```

Pre-commit hooks: `black`, `flake8`, `isort`, `checkov`, `gitleaks`.

---

## Architecture

### Data Flow

```
Oracle WMS
  ├─[CDC]──► DMS → Kinesis → Lambda Consumer ──► S3 Bronze (Iceberg)
  └─[batch]─► Airflow → Lambda (cx_Oracle) ─────────────────────────►│
                                                                       │
                  ViaCEP + IBGE + INMET + ANTT                        │
                    Lambda Enrichment + SQS ──────────────────────────►│
                                                                       ▼
                                                         dbt + Glue (Spark) → S3 Silver (Iceberg)
                                                         dbt + Glue (Spark) → S3 Gold (Iceberg)
                                                         Redshift COPY → Redshift Serverless
                                                                       │
                                                    ┌──────────────────┤
                                               AI Agents           Grafana
                                          AnalystAgent (SQL)       4 Dashboards
                                          ResearchAgent (RAG)
                                          ReporterAgent (synthesis)
                                                    │
                                               FastAPI (Lambda + API Gateway)
                                                    │
                                             React + Vite (S3 + CloudFront)
```

### Layer-by-Layer Summary

| Layer | Location | Technology |
|---|---|---|
| Orchestration | `pipelines/dags/` | Apache Airflow (Astronomer Cloud, 7 DAGs) |
| Batch extraction | `pipelines/extraction/` | Lambda + cx_Oracle, checkpoint in S3 |
| CDC | `pipelines/cdc/` | AWS DMS → Kinesis → `kinesis_consumer.py` |
| Enrichment | `pipelines/enrichment/` | Lambda + SQS, APIs: ViaCEP/IBGE/INMET/ANTT |
| Data Lake | S3 buckets | Apache Iceberg (bronze/silver/gold), Glue Catalog |
| Transformations | `transform/dbt_wms/` | dbt Core on AWS Glue (Spark) |
| Warehouse | Redshift Serverless | 8 analytical marts, Redshift Spectrum for Iceberg |
| AI Agents | `app/agents/` | LangChain/CrewAI, Claude Haiku via Bedrock, Qdrant RAG |
| API | `app/api/` | FastAPI on Lambda + API Gateway + WAF |
| Frontend | `web/` | React + Vite, S3 + CloudFront |
| Infrastructure | `infra/terraform/` | 15 Terraform modules |

### Key Architectural Decisions

- **Iceberg over Delta Lake** (ADR-001): Native AWS integration with Glue Catalog, Glue jobs, and Redshift Spectrum.
- **DMS CDC over timestamp extraction** (ADR-002): Captures DELETEs and multiple UPDATEs per transaction; no dependency on `updated_at`.
- **Glue for dbt transforms, Redshift for serving** (ADR-003): Separation of concerns — managed Spark transform vs. optimized analytical queries.
- **Kinesis over Kafka** (ADR-004): Volume does not justify Kafka; Kinesis free tier is sufficient.
- **Lambda over EC2/ECS** (ADR-005): Zero cost at idle, auto-scale, adequate for 8GB batch jobs.

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

### S3 Buckets

| Bucket | Purpose |
|---|---|
| `wms-dp-{env}-bronze-{region}-{account}` | Raw Oracle data + CDC events (no transformation) |
| `wms-dp-{env}-silver-{region}-{account}` | Normalized, deduped, typed, geocoded, enriched |
| `wms-dp-{env}-gold-{region}-{account}` | Aggregated marts ready for consumption |
| `wms-dp-{env}-artifacts-{region}-{account}` | Checkpoints, API response cache, dbt artifacts |
| `wms-dp-{env}-query-results-{region}-{account}` | query results and transient artifacts (7-day lifecycle) |
| `wms-dp-{env}-frontend-{region}-{account}` | React build (served via CloudFront OAC) |
| `wms-data-platform-tf-state-896159010925` | Terraform remote state (versioning + MFA delete) |

### CI/CD (GitHub Actions — 7 workflows)

| Workflow | Trigger |
|---|---|
| `ci.yml` | PR — lint, tests, dbt compile, tf validate |
| `deploy-infra.yml` | PR plan / merge apply |
| `deploy-lambda.yml` | Docker build → ECR → Lambda update |
| `deploy-frontend.yml` | React build → S3 sync → CloudFront invalidation |
| `dbt-run.yml` | Scheduled daily dbt run + test |
| `security-scan.yml` | checkov, bandit, trivy, gitleaks |
| `docs.yml` | dbt docs + API docs → S3 |

Branch strategy: `feature/*` → `dev` → `main`. Production deploys require manual approval.

### External Services (all free tier)

Astronomer Cloud (Airflow), Qdrant Cloud (vector store), Grafana Cloud (dashboards), LangFuse (LLM observability), DeepEval (agent evaluation).

---

## Tech Stack

- **Language**: Python 3.11+
- **IaC**: Terraform (15 modules, remote state on S3 + DynamoDB lock, `dev`/`prod` environments)
- **Security**: WAF + KMS (3 keys) + GuardDuty + CloudTrail + Secrets Manager; least-privilege IAM (1 role per service)
- **Observability**: CloudWatch (6 log groups, 8 alarms), SNS, Grafana Cloud, LangFuse, DeepEval, AWS Budgets ($50/$100/$150/$200 alerts)
- **Local dev**: Docker Compose (Oracle XE + Airflow mock), `devcontainer.json`
