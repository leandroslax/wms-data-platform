# WMS Data Platform

## Project Overview

WMS Data Platform is a portfolio-grade data platform built on top of Oracle WMS.
It combines ingestion, medallion lakehouse modeling on PostgreSQL, analytical serving, operational APIs, and a multi-agent AI layer for grounded analytics and troubleshooting.

## Architecture Summary

- Source: Oracle WMS read-only access
- Ingestion: batch extraction with cx_Oracle and checkpoint
- Lakehouse: PostgreSQL schemas — bronze, silver, gold
- Transform: dbt Core + dbt-postgres
- Serving: PostgreSQL gold schema + FastAPI
- AI Layer: AnalystAgent, ResearchAgent, ReporterAgent
- Interface: React + Vite
- Ops: Airflow (local Docker), Grafana (local Docker), LangFuse, DeepEval

## Directory Focus

```text
pipelines/            # extraction, DAGs, enrichment scripts, checkpoints
transform/dbt_wms/    # dbt project with staging/intermediate/marts
app/api/              # FastAPI application
app/agents/           # WMS analytics and RAG agents
web/                  # frontend
docker/               # Grafana and Airflow Docker configs
docs/                 # architecture, ADRs, runbooks, images
.claude/              # KB, agents, commands, local working memory
```

## Working Rules

- Prefer local-first patterns consistent with Docker Compose architecture.
- Keep all work inside this repository.
- Use typed Python 3.11+ code with production-grade error handling.
- Keep documentation aligned with code changes, especially ADRs and runbooks.
- Treat `docs/runbooks/` as future RAG content and write them clearly.
- Preserve security posture: least privilege, no secrets in code, gitleaks in pre-commit.

## Preferred Build Order

1. Docker Compose stack (PostgreSQL + Airflow + Grafana)
2. Extraction layer and checkpoints
3. dbt project and model contracts
4. API and PostgreSQL gold access layer
5. Agents and retrieval layer
6. Frontend and dashboards
7. CI/CD hardening and observability

## Main Agents

- `AnalystAgent`: SQL-first analysis over PostgreSQL gold marts
- `ResearchAgent`: semantic retrieval over runbooks, ADRs, incidents, and docs
- `ReporterAgent`: synthesis of structured and semantic context into executive or operational answers

## KB Priorities

When working on this repository, prioritize these KB domains first:

- `wms`
- `architecture`
- `python`
- `testing`
- `langchain`
- `crewai`
- `langfuse`
- `deepeval`

## Delivery Style

Prefer scaffolds that are production-shaped even when implementations are still placeholders.
That means realistic file names, interfaces, workflow names, and documentation boundaries.
