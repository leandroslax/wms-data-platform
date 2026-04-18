PYTHON  ?= python3
PIP     ?= pip3
COMPOSE  = docker compose
DBT      = dbt run --project-dir transform/dbt_wms --profiles-dir transform/dbt_wms

.PHONY: help up down restart logs seed \
        dbt-run dbt-test dbt-docs dbt-seed \
        api-dev lint test \
        tf-plan tf-apply

# ── Docker ─────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make up          → sobe toda a stack Docker"
	@echo "  make down        → para e remove containers"
	@echo "  make logs        → tail -f todos os serviços"
	@echo "  make seed        → popula bronze com dados de amostra"
	@echo "  make dbt-run     → roda todos os modelos (target=local)"
	@echo "  make dbt-test    → roda testes dbt"
	@echo "  make dbt-docs    → gera e abre docs dbt"
	@echo "  make api-dev     → FastAPI com hot-reload (sem Docker)"
	@echo ""

up:
	@cp -n .env.example .env 2>/dev/null || true
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  ✅  Stack rodando:"
	@echo "      PostgreSQL   → localhost:5432"
	@echo "      Qdrant       → localhost:6333"
	@echo "      MinIO        → localhost:9001  (user: wmsadmin)"
	@echo "      API          → http://localhost:8000/docs"
	@echo "      Airflow      → http://localhost:8080  (admin/admin)"
	@echo ""

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

# ── Seed & dbt ─────────────────────────────────────────────────

seed:
	@echo "Populando bronze com dados de amostra..."
	$(PYTHON) docker/postgres/seed.py
	@echo "✅  Seed concluído."

dbt-run: seed
	$(DBT) --target local

dbt-test:
	dbt test --project-dir transform/dbt_wms --profiles-dir transform/dbt_wms --target local

dbt-docs:
	dbt docs generate --project-dir transform/dbt_wms --profiles-dir transform/dbt_wms --target local
	dbt docs serve  --project-dir transform/dbt_wms --profiles-dir transform/dbt_wms

dbt-validate:
	$(PYTHON) transform/validate_marts_duckdb.py

# ── API (dev local sem Docker) ─────────────────────────────────

api-dev:
	uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# ── Qualidade ──────────────────────────────────────────────────

lint:
	black app pipelines tests
	isort app pipelines tests
	flake8 app pipelines tests

test:
	pytest tests -v

# ── Terraform (manter para referência de arquitetura) ──────────

tf-plan:
	cd infra/terraform/envs/dev && terraform init && terraform plan

tf-apply:
	cd infra/terraform/envs/dev && terraform init && terraform apply -auto-approve
