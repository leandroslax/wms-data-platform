PYTHON  ?= python3
PIP     ?= pip3
COMPOSE  = docker compose
DBT      = dbt run --project-dir transform/dbt_wms --profiles-dir transform/dbt_wms

.PHONY: help up down restart logs seed \
        extract extract-full clean-bronze pipeline-real \
        dbt-run dbt-run-demo dbt-test dbt-docs dbt-seed \
        api-dev lint test \
        tf-plan tf-apply

# ── Docker ─────────────────────────────────────────────────────

help:
	@echo ""
	@echo ""
	@echo "  make up             → sobe toda a stack Docker"
	@echo "  make down           → para e remove containers"
	@echo "  make logs           → tail -f todos os serviços"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make pipeline-real  → limpa bronze + Oracle + dbt full-refresh"
	@echo "  make clean-bronze   → trunca tabelas bronze e reseta watermarks"
	@echo "  make extract        → extração incremental Oracle → bronze"
	@echo "  make extract-full   → extração full 90 dias Oracle → bronze"
	@echo "  make dbt-run        → dbt sobre dados atuais do bronze"
	@echo "  make dbt-run-demo   → seed (demo) + dbt"
	@echo "  ──────────────────────────────────────────────"
	@echo "  make dbt-test       → roda testes dbt"
	@echo "  make dbt-docs       → gera e abre docs dbt"
	@echo "  make api-dev        → FastAPI com hot-reload (sem Docker)"
	@echo ""

up:
	@cp -n .env.example .env 2>/dev/null || true
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  ✅  Stack rodando:"
	@echo "      Chat (gestor) → http://localhost:8000"
	@echo "      Grafana       → http://localhost:3000  (admin/wmsadmin2026)"
	@echo "      Airflow       → http://localhost:8080  (admin/admin)"
	@echo "      API Docs      → http://localhost:8000/docs"
	@echo "      Qdrant        → http://localhost:6333"
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

extract:
	@echo "Extraindo dados reais do Oracle WMS → PostgreSQL bronze..."
	$(PYTHON) pipelines/extraction/oracle_to_postgres.py --mode incremental
	@echo "✅  Extração concluída."

extract-full:
	@echo "Extração full 90 dias do Oracle WMS → PostgreSQL bronze..."
	$(PYTHON) pipelines/extraction/oracle_to_postgres.py --mode full_90d
	@echo "✅  Extração full concluída."

clean-bronze:
	@echo "Limpando tabelas bronze (remove seed e dados antigos)..."
	docker compose exec -T postgres psql -U wmsadmin -d wms -c \
	  "TRUNCATE bronze.orders_documento, bronze.inventory_produtoestoque, bronze.movements_entrada_saida, bronze.products_snapshot;"
	@rm -f artifacts/extraction/_watermarks.json
	@echo "✅  Bronze limpo. Rode 'make extract-full' para recarregar dados reais."

# Pipeline completo: limpa bronze → extrai Oracle → transforma com dbt
pipeline-real:
	@echo "=== Pipeline completo: Oracle → bronze → gold ==="
	$(MAKE) clean-bronze
	$(MAKE) extract-full
	DBT_BRONZE_SCHEMA=bronze $(DBT) --target local --full-refresh
	@echo "✅  Pipeline concluído com dados reais."

dbt-run:
	@echo "Rodando dbt sobre os dados existentes no bronze (Oracle real ou seed)..."
	DBT_BRONZE_SCHEMA=bronze $(DBT) --target local

dbt-run-demo: seed
	@echo "Rodando dbt com dados de demonstração (seed)..."
	DBT_BRONZE_SCHEMA=bronze $(DBT) --target local

dbt-test:
	DBT_BRONZE_SCHEMA=bronze dbt test --project-dir transform/dbt_wms --profiles-dir transform/dbt_wms --target local

dbt-docs:
	DBT_BRONZE_SCHEMA=bronze dbt docs generate --project-dir transform/dbt_wms --profiles-dir transform/dbt_wms --target local
	dbt docs serve --project-dir transform/dbt_wms --profiles-dir transform/dbt_wms --port 8081

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
