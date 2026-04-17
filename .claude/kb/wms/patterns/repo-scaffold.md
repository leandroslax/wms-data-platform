# WMS Repo Scaffold Pattern

Use a layered repository structure that mirrors the platform architecture.

## Rules

1. Infrastructure lives in `infra/terraform/` with modules and envs.
2. Ingestion and orchestration live in `pipelines/`.
3. Transform logic lives in `transform/dbt_wms/`.
4. Product-facing code lives in `app/` and `web/`.
5. Architecture, ADRs, and runbooks live in `docs/`.
6. Claude-specific context lives in `.claude/` and must reference WMS, not ShopAgent.
