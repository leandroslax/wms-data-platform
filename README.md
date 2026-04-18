# WMS Data Platform

Plataforma de dados moderna construída sobre Oracle WMS, cobrindo o ciclo completo de engenharia de dados: ingestão incremental com Parquet, lakehouse medallion no S3 com Apache Iceberg, transformações dbt no Glue, warehouse analítico no Redshift Serverless e camada de agentes de IA conversacional.

---

## Arquitetura

```
Oracle WMS (read-only, via VPN FortiGate)
    │
    ├─[batch]──► Lambda Extrator (export_oraint_parquet.py)
    │             checkpoint incremental por PK no S3
    │                       │
    │                       ▼
    │            S3 Raw (Parquet bruto)        ← Landing zone
    │                       │
    │            raw_to_bronze_iceberg.py
    │                       │
    └─[CDC]──► DMS → Kinesis → Lambda Consumer
                              │
                              ▼
                   S3 Bronze (Iceberg MERGE)   ← Fonte única de verdade
                   Glue Data Catalog
                              │
                   dbt Core + AWS Glue (Spark)
                              │
                   S3 Silver (Iceberg)         ← Normalizado, dedupado, tipado
                              │
                   dbt marts analíticos
                              │
                   S3 Gold (Iceberg)           ← Agregados prontos para consumo
                              │
                   Redshift COPY
                              │
                   Redshift Serverless         ← Serving layer
                         │         │
                    Agentes IA   Grafana Cloud
               AnalystAgent       4 dashboards
               ResearchAgent
               ReporterAgent
                    │
               FastAPI (Lambda + API Gateway + WAF)
                    │
               React + Vite (S3 + CloudFront)
```

---

## Status por Camada

### ✅ Infraestrutura (Terraform)

- Remote state: S3 + DynamoDB lock
- Ambientes separados: `dev` e `prod` aplicados
- Módulos implementados e aplicados: `iam`, `s3`, `ecr`, `lambda`, `monitoring`, `secrets`
- Módulos implementados mas **não aplicados**: `redshift`, `api_gateway`, `cloudfront`, `waf`, `athena`, `budget`, `cloudtrail`, `vpc`, `eventbridge`
- Módulos pendentes para CDC: `dms`, `kinesis`, `sqs`
- IAM: roles com prefixo de ambiente (`dev`/`prod`), policy KMS gerenciada pelo Terraform
- Buckets S3 ativos: `raw`, `bronze`, `silver`, `gold`, `artifacts`, `query-results`, `frontend` (dev + prod)

---

### ✅ Extração (Raw Layer)

- `export_oraint_parquet.py`: extrator incremental Oracle WMS → Parquet → S3 raw
- Entidades ativas: `orders_documento`, `inventory_produtoestoque`, `movements_entrada_saida`, `products_snapshot`
- Checkpoint por PK no S3 (`artifacts`), suporte a `incremental` e `snapshot_full`
- Anonimização de dados sensíveis (`anonymizer.py`)
- Upload particionado: `entity={name}/date={YYYY-MM-DD}/`

---

### ✅ Bronze (Iceberg)

- `raw_to_bronze_iceberg.py`: lê Parquet do raw, faz UPSERT para Iceberg via PyIceberg + Glue Catalog
- Tabelas Iceberg registradas no Glue Catalog (`wms_bronze_dev`, `wms_bronze_prod`)
- MERGE por chave de negócio por entidade
- CDC via DMS + Kinesis: **módulos Terraform prontos, aguardando liberação de IP na VPN FortiGate**

---

### ✅ Silver (dbt + Glue)

- dbt Core 1.10 + dbt-glue 1.10 rodando no AWS Glue (Spark)
- **19/19 testes passando** com dados reais do Oracle WMS
- Targets separados: `dev` (Glue → `wms_silver_dev`) e `prod` (Glue → `wms_silver_prod`)
- Schema dinâmico via `DBT_BRONZE_SCHEMA` env var

Modelos ativos:

| Modelo | Tipo | Chave | Descrição |
|---|---|---|---|
| `stg_inventory` | view | `inventory_id` | Estoque normalizado, dedup por `sequenciaestoque` |
| `stg_movements` | view | `movement_id` | Movimentações, dedup por `sequenciamovimento` |
| `stg_orders` | view | `order_id` | Documentos de saída, dedup por `SEQUENCIADOCUMENTO` |
| `fct_inventory_snapshot` | incremental Iceberg | `inventory_id` | Posição de estoque por produto/armazém |
| `fct_movements` | incremental Iceberg | `movement_id` | Movimentações com delta de quantidade |
| `fct_orders` | incremental Iceberg | `order_id` | Documentos de saída com valores |
| `dim_products` | incremental Iceberg | `product_id` | Dimensão produto deduplicated |

---

### ❌ Gold — Marts Analíticos (próximo passo)

Os 8 marts analíticos estão planejados na arquitetura mas **ainda não implementados** no dbt:

| Mart | Descrição | Depende de |
|---|---|---|
| `mart_picking_performance` | Produtividade por operador e turno | `fct_movements`, dados de tasks |
| `mart_inventory_health` | Giro, cobertura e risco de ruptura | `fct_inventory_snapshot` |
| `mart_order_sla` | Tempo de ciclo e aderência ao prazo | `fct_orders` |
| `mart_operator_productivity` | Ranking com contexto de complexidade | `fct_movements`, `fct_orders` |
| `mart_stockout_risk` | Projeção de ruptura por SKU | `fct_inventory_snapshot` |
| `mart_geo_performance` | SLA por estado/cidade | `fct_orders` + enriquecimento CEP |
| `mart_geo_inventory` | Cobertura de estoque por região | `fct_inventory_snapshot` + enriquecimento CEP |
| `mart_weather_impact` | Correlação atraso × clima | `fct_orders` + INMET |

---

### ❌ Redshift Serverless (bloqueado pelos marts)

- Módulo Terraform `modules/redshift` existe mas não foi aplicado
- Aguarda: (1) marts gold implementados no dbt, (2) `terraform apply` no módulo
- Após provisionamento: carregar marts via Redshift COPY do S3 gold

---

### ⚠️ Agents IA (código pronto, sem dados)

Código implementado e estruturado, mas **não funcionais** até o Redshift estar provisionado:

| Agent | Arquivo | Status |
|---|---|---|
| `AnalystAgent` | `app/agents/analyst_agent.py` | ✅ implementado — aguarda Redshift |
| `ResearchAgent` | `app/agents/research_agent.py` | ✅ implementado — aguarda Qdrant indexado |
| `ReporterAgent` | `app/agents/reporter_agent.py` | ✅ implementado — aguarda os dois acima |
| `WMSCrew` | `app/agents/wms_crew.py` | ✅ implementado — entry point `run_wms_crew()` |
| `redshift_tool` | `app/agents/tools/redshift_tool.py` | ✅ implementado |
| `qdrant_tool` | `app/agents/tools/qdrant_tool.py` | ✅ implementado |

Stack: CrewAI + LangChain + Claude Haiku (Bedrock) + Qdrant Cloud + LangFuse + DeepEval

---

### ⚠️ API FastAPI (skeleton)

Estrutura de rotas e schemas criada, mas **sem lógica de negócio** conectada aos agents ou ao Redshift:

- `app/api/routes/`: `health`, `inventory`, `movements`, `orders`, `metadata`
- `app/api/services/`: `data_access`, `inventory_service`, `movements_service`, `orders_service`
- Falta: rota `/chat` conectada ao `run_wms_crew()`, serviços conectados ao Redshift

---

### ❌ Orquestração Airflow (stubs)

6 DAGs escritas como placeholders no Astronomer Cloud — lógica interna pendente:

| DAG | Schedule | Status |
|---|---|---|
| `dag_extract_wms.py` | diário 01h | stub |
| `dag_transform_dbt.py` | diário 03h | stub |
| `dag_quality_check.py` | diário 04h | stub |
| `dag_load_warehouse.py` | diário 04h30 | stub |
| `dag_embed_rag.py` | semanal | stub |
| `dag_freshness_monitor.py` | horário | stub |

---

### ❌ Enriquecimento Geográfico/Climático

Não iniciado. Necessário para `mart_geo_performance`, `mart_geo_inventory` e `mart_weather_impact`:
- ViaCEP → CEP para cidade, estado, lat/long
- IBGE → dados demográficos por município
- INMET → histórico climático por cidade/data
- ANTT → dados de transportadoras

---

### ❌ Frontend React

Não iniciado. Previsto: `ChatInterface`, `InventoryDashboard`, `OperationsDashboard`, `GeoMapDashboard`.

---

## Roadmap

```
CONCLUÍDO
─────────────────────────────────────────────────
✅ Terraform foundation (dev + prod)
✅ Raw layer (S3 + extrator Parquet)
✅ Bronze layer (Iceberg MERGE, Glue Catalog)
✅ Silver layer (dbt 19/19 testes, 7 modelos)
✅ Agents code (Crew, tools, Redshift + Qdrant)
✅ KB e sub-agents Claude Code (.claude/)

PRÓXIMO PASSO
─────────────────────────────────────────────────
⬜ Gold layer — implementar 8 marts no dbt
   (mart_picking_performance, mart_order_sla,
    mart_inventory_health, mart_operator_productivity,
    mart_stockout_risk, mart_geo_performance,
    mart_geo_inventory, mart_weather_impact)

EM SEQUÊNCIA
─────────────────────────────────────────────────
⬜ Redshift Serverless — terraform apply + COPY do gold
⬜ Agents funcionais — conectar ao Redshift provisionado
⬜ Qdrant — indexar runbooks e ADRs (dag_embed_rag)
⬜ FastAPI — rota /chat + serviços conectados
⬜ DAGs Airflow — implementar lógica interna
⬜ CDC — liberar IP na VPN FortiGate + ativar DMS/Kinesis
⬜ Enriquecimento — ViaCEP, IBGE, INMET, ANTT
⬜ Frontend React — ChatInterface + dashboards
⬜ CI/CD — 7 GitHub Actions workflows
⬜ Observabilidade — LangFuse, DeepEval, Grafana
```

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| IaC | Terraform (17 módulos, remote state S3 + DynamoDB) |
| Extração | Lambda + oracledb, checkpoint incremental |
| Ingestão | PyIceberg + Glue Catalog (raw → bronze MERGE) |
| Transformação | dbt Core 1.10 + dbt-glue 1.10 (Spark no Glue) |
| Formato de tabela | Apache Iceberg (bronze, silver, gold) |
| Warehouse | Amazon Redshift Serverless |
| Agentes | CrewAI + LangChain, Claude Haiku via Bedrock |
| Vetores | Qdrant Cloud (runbooks, ADRs, docs) |
| API | FastAPI + Lambda + API Gateway + WAF |
| Frontend | React + Vite + S3 + CloudFront |
| Orquestração | Apache Airflow (Astronomer Cloud) |
| Segurança | KMS, GuardDuty, CloudTrail, WAF, Secrets Manager |
| Observabilidade | CloudWatch, LangFuse, DeepEval, Grafana Cloud |
| CI/CD | GitHub Actions (7 workflows) |

---

## Estrutura do Repositório

```
infra/terraform/
  modules/          # 17 módulos AWS (iam, s3, lambda, redshift, vpc, ...)
  envs/dev/         # aplicado ✅
  envs/prod/        # aplicado ✅

pipelines/
  extraction/       # extratores Oracle → S3 raw ✅
  ingestion/        # raw → bronze Iceberg ✅
  dags/             # 6 DAGs Airflow (stubs) ⚠️
  cdc/              # Kinesis consumer (pendente CDC) ❌
  enrichment/       # ViaCEP, IBGE, INMET, ANTT ❌

transform/dbt_wms/
  models/staging/   # 3 staging views ✅
  models/marts/     # 4 fct/dim básicos ✅ | 8 marts analíticos ❌

app/
  agents/           # AnalystAgent, ResearchAgent, ReporterAgent, WMSCrew ✅ (sem Redshift)
  api/              # FastAPI skeleton ⚠️

web/                # React + Vite ❌

docs/               # arquitetura, ADRs, runbooks
.claude/            # KB (18 domínios), sub-agents, comandos
```

---

## Ambientes

| Recurso | dev | prod |
|---|---|---|
| Glue role | `wms-data-platform-dev-glue-role` | `wms-data-platform-prod-glue-role` |
| S3 buckets | `wms-dp-dev-*` | `wms-dp-prod-*` |
| dbt target | `wms_silver_dev` | `wms_silver_prod` |
| ECR | `wms-data-platform-dev-lambda` | `wms-data-platform-prod-lambda` |
| Lambdas | `wms-data-platform-dev-{api,extractor,embedder}` | `wms-data-platform-prod-*` |
