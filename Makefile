PYTHON ?= python3
PIP ?= pip3

.PHONY: setup extract dbt-run dbt-test api-dev web-dev tf-plan tf-apply test lint docs

setup:
	$(PIP) install -r requirements.txt
	pre-commit install

extract:
	$(PYTHON) pipelines/lambda_handler.py

dbt-run:
	dbt run --project-dir transform/dbt_wms

dbt-test:
	dbt test --project-dir transform/dbt_wms

api-dev:
	uvicorn app.api.main:app --reload

web-dev:
	cd web && npm install && npm run dev

tf-plan:
	cd infra/terraform/envs/dev && terraform init && terraform plan

tf-apply:
	cd infra/terraform/envs/dev && terraform init && terraform apply -auto-approve

test:
	pytest tests

lint:
	black app pipelines tests
	isort app pipelines tests
	flake8 app pipelines tests

docs:
	dbt docs generate --project-dir transform/dbt_wms
