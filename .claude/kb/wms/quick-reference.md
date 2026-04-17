# WMS Quick Reference

## Core Flow

`Oracle WMS -> extraction/CDC -> S3 bronze -> dbt/Glue -> S3 silver/gold -> Redshift -> API/agents/web`

## Primary Components

- `infra/terraform/`: AWS foundation
- `pipelines/`: extraction and orchestration
- `transform/dbt_wms/`: transformations and tests
- `app/api/`: serving layer
- `app/agents/`: AnalystAgent, ResearchAgent, ReporterAgent
- `docs/runbooks/`: future RAG corpus

## Domain Priorities

- preserve source traceability in bronze
- concentrate business logic in dbt intermediate and marts
- expose low-latency answers through Redshift and API services
- use runbooks and docs as the semantic memory for the AI layer

## Non-Negotiables

- Multi-env Terraform
- Least-privilege IAM
- KMS for sensitive storage and secrets
- Documented ADRs for major trade-offs
- Runbooks written as reusable operational memory
- WMS naming, never ShopAgent leftovers
