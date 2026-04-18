# WMS Data Platform

Plataforma de dados moderna construída sobre Oracle WMS, cobrindo o ciclo completo de engenharia de dados: ingestão incremental, arquitetura medallion local, transformações dbt, serving via PostgreSQL e camada de agentes de IA conversacional com RAG.

> Toda a stack roda localmente via Docker Compose — sem dependência de nuvem.

---

## Quick Start

```bash
git clone https://github.com/leandrolps/wms-data-platform.git
cd wms-data-platform

cp .env.example .env          # preencha ANTHROPIC_API_KEY e LANGFUSE_*

make up                       # sobe PostgreSQL, Qdrant, MinIO, Airflow e API
make dbt-run                  # seed bronze → dbt run (8 marts no gold)
make dbt-test                 # roda os testes dbt
```

Serviços disponíveis após `make up`:

| Serviço | URL |
|---|---|
| API FastAPI | http://localhost:8000 |
| Docs interativos | http://localhost:8000/docs |
| Airflow | http://localhost:8080 (admin/admin) |
| MinIO Console | http://localhost:9001 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## Arquitetura

```
Dados de exemplo (seed.py)
         │
         ▼
  PostgreSQL — schema bronze     ← Fonte única de verdade (local)
         │
  dbt Core (target: local)
         │
  PostgreSQL — schema silver     ← Normalizado, dedupado, tipado
         │
  dbt marts analíticos
         │
  PostgreSQL — schema gold       ← 8 marts prontos para consumo
         │
         ├──► Agentes IA
         │    AnalystAgent  (SQL sobre gold)
         │    ResearchAgent (RAG sobre runbooks/ADRs)
         │    ReporterAgent (síntese executiva)
         │         │
         │    FastAPI  →  POST /chat
         │
         ├──► Qdrant (local)     ← Vector store para RAG
         ├──► MinIO (local)      ← Object storage (artefatos, checkpoints)
         └──► Airflow (local)    ← Orquestração dos pipelines
```

---

## Status por Camada

### ✅ Infraestrutura Local (Docker Compose)

- PostgreSQL 16 com schemas `bronze`, `silver`, `gold` provisionados via `docker/postgres/init.sql`
- Qdrant v1.9 para vector store local
- MinIO para object storage local (substitui S3)
- Airflow 2 com LocalExecutor (webserver + scheduler)
- FastAPI com hot-reload montado como volume

---

### ✅ Bronze (PostgreSQL local)

Tabelas criadas automaticamente na inicialização do container:

| Tabela | Descrição |
|---|---|
| `bronze.orders_documento` | Documentos de saída (NF, OS, TE) |
| `bronze.inventory_produtoestoque` | Posição de estoque por produto/armazém |
| `bronze.movements_entrada_saida` | Movimentações de entrada e saída |
| `bronze.products_snapshot` | Snapshot de cadastro de produtos |
| `bronze.orders_documentodetalhe` | Itens/linhas de documento |

Dados populados via `make seed` (200 orders, 500 movements, 60 inventory rows, 60 product snapshots).

---

### ✅ Silver (dbt + PostgreSQL)

- dbt Core rodando contra PostgreSQL local (`target: local`)
- Macros de compatibilidade cross-db em `macros/compat.sql` — mesmos modelos rodam em PostgreSQL, DuckDB e Glue/Spark

| Modelo | Tipo | Chave |
|---|---|---|
| `stg_orders` | view | `order_id` |
| `stg_inventory` | view | `inventory_id` |
| `stg_movements` | view | `movement_id` |
| `fct_orders` | table | `order_id` |
| `fct_inventory_snapshot` | table | `inventory_id` |
| `fct_movements` | table | `movement_id` |
| `dim_products` | table | `product_id` |

---

### ✅ Gold — 8 Marts Analíticos

Todos os marts implementados, validados com DuckDB e rodando em PostgreSQL local:

| Mart | Descrição |
|---|---|
| `mart_picking_performance` | Produtividade por operador e turno |
| `mart_inventory_health` | Giro, cobertura e risco de ruptura |
| `mart_order_sla` | Tempo de ciclo e aderência ao prazo |
| `mart_operator_productivity` | Ranking com contexto de complexidade |
| `mart_stockout_risk` | Projeção de ruptura por SKU |
| `mart_geo_performance` | SLA por estado/cidade |
| `mart_geo_inventory` | Cobertura de estoque por região |
| `mart_weather_impact` | Correlação atraso × clima |

---

### ✅ Agentes IA (código pronto)

Stack: CrewAI + LangChain + Claude (Anthropic API) + Qdrant local + LangFuse

| Agent | Arquivo | Função |
|---|---|---|
| `AnalystAgent` | `app/agents/analyst_agent.py` | SQL sobre marts gold |
| `ResearchAgent` | `app/agents/research_agent.py` | RAG sobre runbooks/ADRs via Qdrant |
| `ReporterAgent` | `app/agents/reporter_agent.py` | Síntese executiva |
| `WMSCrew` | `app/agents/wms_crew.py` | Orquestra os três agentes em sequência |

---

### ✅ API FastAPI

- `GET /health` — status da API
- `POST /chat` — pergunta em linguagem natural → resposta via WMSCrew
- `GET /inventory`, `/movements`, `/orders` — endpoints de consulta direta

---

### ⚠️ Orquestração Airflow (stubs)

6 DAGs escritas como placeholders — lógica interna pendente:

| DAG | Schedule |
|---|---|
| `dag_extract_wms.py` | diário 01h |
| `dag_transform_dbt.py` | diário 03h |
| `dag_quality_check.py` | diário 04h |
| `dag_load_warehouse.py` | diário 04h30 |
| `dag_embed_rag.py` | semanal |
| `dag_freshness_monitor.py` | horário |

---

### ❌ Enriquecimento Geográfico/Climático

Pendente para `mart_geo_performance`, `mart_geo_inventory` e `mart_weather_impact`:
- ViaCEP — CEP → cidade, estado, coordenadas
- IBGE — dados demográficos por município
- INMET — histórico climático por cidade/data
- ANTT — dados de transportadoras

---

### ❌ Frontend React

Não iniciado. Previsto: `ChatInterface`, `InventoryDashboard`, `OperationsDashboard`, `GeoMapDashboard`.

---

## Roadmap

```
CONCLUÍDO
─────────────────────────────────────────────────
✅ Docker Compose (PostgreSQL, Qdrant, MinIO, Airflow, API)
✅ Bronze — tabelas e seed de dados
✅ Silver — 7 modelos dbt (staging + fct + dim)
✅ Gold — 8 marts analíticos implementados e validados
✅ dbt cross-db compat (PostgreSQL, DuckDB, Glue/Spark)
✅ Agentes (AnalystAgent, ResearchAgent, ReporterAgent, WMSCrew)
✅ API FastAPI com rota /chat
✅ KB e documentação (.claude/)

EM ANDAMENTO
─────────────────────────────────────────────────
⬜ DAGs Airflow — implementar lógica interna
⬜ Qdrant — indexar runbooks e ADRs (dag_embed_rag)
⬜ Agentes — testes de integração com PostgreSQL local

PRÓXIMOS PASSOS
─────────────────────────────────────────────────
⬜ Enriquecimento — ViaCEP, IBGE, INMET, ANTT
⬜ Frontend React — ChatInterface + dashboards
⬜ CI/CD — GitHub Actions (lint, test, dbt compile)
⬜ Observabilidade — LangFuse traces, DeepEval evals, Grafana
```

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Banco de dados | PostgreSQL 16 (bronze / silver / gold) |
| Object storage | MinIO (local) |
| Transformação | dbt Core 1.10 + dbt-postgres |
| Agentes | CrewAI + LangChain + Claude (Anthropic API) |
| Vector store | Qdrant (local) |
| API | FastAPI + Uvicorn |
| Orquestração | Apache Airflow 2 (LocalExecutor) |
| Observabilidade | LangFuse, DeepEval |
| Infra local | Docker Compose |

---

## Estrutura do Repositório

```
docker/
  postgres/
    init.sql          # cria schemas e tabelas bronze
    seed.py           # popula bronze com dados de amostra

transform/dbt_wms/
  models/staging/     # 3 views (stg_orders, stg_inventory, stg_movements)
  models/intermediate/# fct e dim (7 modelos)
  models/marts/       # 8 marts analíticos gold ✅
  macros/compat.sql   # wms_epoch, wms_hour, wms_today (cross-db)
  profiles.yml        # target local (PostgreSQL) + dev/prod (Glue)

app/
  agents/             # AnalystAgent, ResearchAgent, ReporterAgent, WMSCrew
  api/                # FastAPI: main, routes, schemas, services
  requirements.txt
  Dockerfile

pipelines/
  extraction/         # extratores Oracle → bronze (para produção futura)
  dags/               # 6 DAGs Airflow (stubs)
  enrichment/         # ViaCEP, IBGE, INMET, ANTT (pendente)

web/                  # React + Vite (não iniciado)

docs/                 # arquitetura, ADRs, runbooks
.claude/              # KB (18 domínios), sub-agents, comandos

docker-compose.yml
Makefile
.env.example
```

---

## Comandos Úteis

```bash
make up           # sobe todos os serviços (--build incluso)
make down         # para e remove os containers
make seed         # popula bronze com dados de amostra
make dbt-run      # seed + dbt run --target local
make dbt-test     # dbt test --target local
make dbt-docs     # gera e serve dbt docs em localhost:8080
make dbt-validate # valida marts com DuckDB (sem Docker)
make api-dev      # uvicorn local sem Docker (dev rápido)
make logs         # docker compose logs -f
```
