# WMS Data Platform

## Project Overview

WMS Data Platform is a portfolio-grade data platform built on top of Oracle WMS.
It combines ingestion, lakehouse modeling, warehouse serving, operational APIs, and a multi-agent AI layer for grounded analytics and troubleshooting.

## Architecture Summary

- Source: Oracle WMS read-only access
- Ingestion: batch extraction plus CDC-oriented design
- Lakehouse: S3 bronze, silver, gold
- Transform: dbt on Glue (Spark)
- Serving: Redshift Serverless + FastAPI
- AI Layer: AnalystAgent, ResearchAgent, ReporterAgent
- Interface: React + Vite on S3 + CloudFront
- Ops: Airflow, CloudWatch, Grafana Cloud, LangFuse, DeepEval

## Directory Focus

```text
infra/terraform/      # AWS foundation, security, networking, compute, monitoring
pipelines/            # extraction, DAGs, handlers, checkpoints
transform/dbt_wms/    # dbt project with staging/intermediate/marts
app/api/              # FastAPI application
app/agents/           # WMS analytics and RAG agents
web/                  # frontend
.docs/                # architecture, ADRs, runbooks, images
.claude/              # KB, agents, commands, local working memory
```

## Working Rules

- Prefer AWS-native patterns that reinforce the architecture in `docs/architecture.md`.
- Keep all work inside this repository.
- Use Terraform modules and environment separation for infrastructure changes.
- Use typed Python 3.11+ code with production-grade error handling.
- Keep documentation aligned with code changes, especially ADRs and runbooks.
- Treat `docs/runbooks/` as future RAG content and write them clearly.
- Preserve security posture: least privilege, KMS, WAF, CloudTrail, budgets, and secret isolation.

## Preferred Build Order

1. Terraform foundation and remote state
2. Extraction layer and checkpoints
3. dbt project and model contracts
4. API and warehouse access layer
5. Agents and retrieval layer
6. Frontend and dashboards
7. CI/CD hardening and observability

## Main Agents

- `AnalystAgent`: SQL-first analysis over marts and warehouse views
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
