# WMS Data Platform

Plataforma de dados moderna construída sobre Oracle WMS, cobrindo o ciclo completo de engenharia de dados: extração incremental com watermark, arquitetura medallion no PostgreSQL local, transformações dbt Core, orquestração Airflow, serving via FastAPI, camada de agentes de IA conversacional com RAG, e dashboards operacionais no Grafana e Apache Superset.

> A stack local roda via Docker Compose. A extração de dados requer acesso VPN ao Oracle WMS (host `172.31.200.25`, service `WMS`).

---

## Diagrama de Arquitetura

![Diagrama de arquitetura do WMS Data Platform](docs/images/wms-architecture.png)

---

## Quick Start

```bash
git clone https://github.com/leandrolps/wms-data-platform.git
cd wms-data-platform

cp .env.example .env          # preencha ANTHROPIC_API_KEY + credenciais Oracle

docker compose up -d

make extract-full             # extrai 1 ano do Oracle WMS → bronze
docker exec wms-airflow-webserver bash -c \
  "dbt run --project-dir /opt/airflow/dbt_wms --profiles-dir /opt/airflow/dbt_wms"

# Indexa ADRs/runbooks no Qdrant para o ResearchAgent
python3 pipelines/rag/embed_docs.py --docs-dir docs --qdrant-url http://localhost:6333
```

### Serviços disponíveis após `docker compose up`

| Serviço | URL | Acesso |
|---|---|---|
| API FastAPI | http://localhost:8000 | sem autenticação |
| Chat (UI) | http://localhost:8000/chat | sem autenticação |
| Docs interativos | http://localhost:8000/docs | sem autenticação |
| **Grafana** | http://localhost:3000 | requer login |
| **LangFuse** | http://localhost:3001 | requer login |
| **Apache Superset** | http://localhost:8088 | requer login |
| Airflow | http://localhost:8080 | requer login |
| Qdrant Dashboard | http://localhost:6333/dashboard | sem autenticação |

---

## Arquitetura por Camada

### Bronze — Extração

| Tabela | Fonte Oracle | Modo | Volume |
|---|---|---|---|
| `bronze.orders_documento` | `ORAINT.DOCUMENTO` | watermark (DATAEMISSAO) | 5.480 docs |
| `bronze.movements_entrada_saida` | `WMAS.MOVIMENTOENTRADASAIDA` | watermark (DATAHISTORICO) | 887.619 movim. |
| `bronze.inventory_produtoestoque` | `WMAS.ESTOQUEPRODUTO` | snapshot | 4 posições |
| `bronze.products_snapshot` | `ORAINT.PRODUTO` | snapshot | 5.423 produtos |

### Silver — dbt Staging

| Modelo | Tipo | Descrição |
|---|---|---|
| `stg_orders` | view | Normaliza pedidos — chave: `order_id` |
| `stg_movements` | view | Normaliza movimentos — chave: `movement_id` |
| `stg_inventory` | view | Normaliza estoque — chave: `inventory_id` |
| `fct_orders` | incremental | Fatos de pedidos com valores |
| `fct_movements` | incremental | Fatos de movimentações com operador |
| `fct_inventory_snapshot` | incremental | Snapshot de estoque por data |
| `dim_products` | incremental | Dimensão produto com classe ABC |

### Gold — 8 Marts Analíticos

| Mart | Descrição | Linhas |
|---|---|---|
| `mart_order_sla` | Tempo de ciclo, SLA e status por pedido — `delivered_at` derivado via proxy `estadomovimento=8` | 5.480 |
| `mart_operator_productivity` | Ranking de operadores com índice de complexidade | — |
| `mart_picking_performance` | Produtividade por operador e turno (picks/h) | — |
| `mart_stockout_risk` | Projeção de ruptura de estoque por SKU | — |
| `mart_inventory_health` | Cobertura, utilização e risco por produto/armazém | — |
| `mart_geo_performance` | SLA por empresa/mês | — |
| `mart_geo_inventory` | Cobertura de estoque por região | 5 |
| `mart_weather_impact` | Correlação atraso × clima | — |

### dbt Lineage

```mermaid
flowchart LR
    classDef bronze fill:#2d6a2d,color:#fff,stroke:none
    classDef silver fill:#1a5f5a,color:#fff,stroke:none
    classDef gold   fill:#1a5a7a,color:#fff,stroke:none

    B1([bronze.inventory_produtoestoque]):::bronze
    B2([bronze.movements_entrada_saida]):::bronze
    B3([bronze.orders_documento]):::bronze
    B4([bronze.orders_documentodetalhe]):::bronze
    B5([bronze.products_snapshot]):::bronze

    S1([stg_inventory]):::silver
    S2([stg_movements]):::silver
    S3O([stg_orders]):::silver

    F1([fct_inventory_snapshot]):::silver
    F2([fct_movements]):::silver
    F3([fct_orders]):::silver
    D1([dim_products · sku x wh]):::silver

    M1([mart_geo_inventory]):::gold
    M2([mart_inventory_health]):::gold
    M3([mart_stockout_risk]):::gold
    M4([mart_operator_productivity]):::gold
    M5([mart_picking_performance]):::gold
    M6([mart_geo_performance]):::gold
    M7([mart_order_sla]):::gold
    M8([mart_weather_impact]):::gold

    B1 --> S1 --> F1
    B1 --> S1 --> D1
    B5 --> D1
    B2 --> S2 --> F2
    B3 --> S3O --> F3
    B4 --> S3O

    F1 --> M1 & M2 & M3
    F2 --> M4 & M5 & M6
    F3 --> M6 & M7 & M8
```

---

## Dashboards

### Grafana — WMS Mapa Geográfico (`wms_geo.json`)

![Grafana — WMS Mapa Geográfico](docs/images/grafana_geo.png)

Dashboard geográfico com **7 painéis**:

| Painel | Tipo | Métrica |
|---|---|---|
| Mapa SLA por Estado | geomap | SLA % por UF (choropleth) |
| Ranking SLA por Estado | table | UF × pedidos × SLA % |
| Armazéns e Empresas | geomap | Localização dos armazéns e empresas |
| Detalhes por Armazém | table | Warehouse × cidade × UF |
| Chuva × Atraso (série temporal) | timeseries | Precipitação × pedidos atrasados por dia |
| SLA por Macro-Região | bar chart | Norte / Nordeste / Centro-Oeste / Sudeste / Sul |
| Temperatura Média por UF | timeseries | °C por estado nos últimos 365 dias |

### Grafana — WMS Operações (`wms_operations.json`)

Dashboard operacional com **15 painéis** e range padrão de **30 dias**:

![Grafana — WMS Operações](docs/images/grafana_operacional.png)

| Painel | Tipo | Métrica |
|---|---|---|
| Total de Pedidos | stat | COUNT fct_orders |
| Pedidos em Aberto | stat (azul) | sla_status = pending |
| Pedidos Atrasados | stat (vermelho) | sla_status = late |
| Total de Movimentos | stat | COUNT fct_movements |
| Produtos em Risco Crítico | stat (vermelho) | risk_level IN (critical, stockout) |
| SLA % no Prazo | stat (verde/amarelo/vermelho) | on_time + on_time_express / total fechado |
| Movimentações por Dia | timeseries (w=16) | DATE_TRUNC diário com `$__timeFilter` — últimos 30 dias |
| SLA por Status | piechart donut | Express / No Prazo / Em Risco / Atrasado / Pendente |
| Volume de Pedidos por Mês | table | 12 meses × empresa × SLA % |
| Faturamento Mensal | table | Últimos 90 dias em R$ |
| Pedidos por Tipo de Documento | table | NF / OS / TE / RE × empresa |
| Top Operadores — Produtividade | table | Movimentos / Qtd por mov / Complexidade |
| Backlog por Faixa de Aging | table | 0-7d / 7-30d / 30-90d / >90d |
| Pedidos em Aberto Mais Antigos | table | Top 15 mais antigos com aging em horas |
| Risco de Stockout por Produto | table | SKU × classe × dias até ruptura × risco colorido |

### Grafana — Pipeline & Airflow (`wms_pipeline.json`)

Dashboard de monitoramento de infraestrutura com **13 painéis**:

![Grafana — Pipeline & Airflow](docs/images/grafana_pipeline.png)

**Seção Airflow** (datasource: `airflow` DB):
- DAG Runs últimas 24h / Sucessos / Falhas / Em Execução
- Histórico de DAG Runs (últimas 30 execuções)
- Task Instances — últimas falhas
- Duração média por task (7 dias)

**Seção ETL Bronze** (datasource: `wms` DB):
- 4 stats de contagem de linhas por tabela bronze
- Última carga por tabela (timestamp de `_cdc_loaded_at`)

**Seção Silver & Gold**:
- Row counts de todas as tabelas silver e gold via `pg_stat_user_tables`

### Apache Superset — WMS Operations

Dashboard com **13 charts** construídos via manipulação direta do SQLite de metadados:

![Superset — WMS Operations](docs/images/superset_wms_operations.png)

O dashboard do Superset complementa o Grafana com uma visão mais analítica da operação, destacando:
- KPIs executivos de pedidos, movimentações, SLA e backlog
- Séries temporais de volume operacional ao longo do ano
- Tabelas analíticas para pedidos, operadores, risco de stockout e picking
- Gráficos de distribuição para SLA e risco de estoque

| Chart | Tipo | Dataset |
|---|---|---|
| Total de Pedidos | big_number_total | fct_orders |
| Total de Movimentos | big_number_total | fct_movements |
| SLA % no Prazo | big_number_total | mart_order_sla |
| Pedidos em Aberto | big_number_total | mart_order_sla |
| Movimentações por Dia | echarts_timeseries_line | fct_movements |
| SLA por Status | pie (donut) | mart_order_sla |
| Volume de Pedidos por Mês | table | mart_order_sla |
| Pedidos por Tipo de Documento | table | fct_orders |
| Top Operadores — Produtividade | table | mart_operator_productivity |
| Ranking Operadores Top 15 | table | mart_operator_productivity |
| Risco de Stockout por Produto | table | mart_stockout_risk |
| Distribuição de Risco de Estoque | pie (donut) | mart_stockout_risk |
| Saúde do Inventário | table | mart_inventory_health |
| Performance de Picking por Turno | table | mart_picking_performance |

> **Script de reconstrução:** `scripts/superset_docker_setup.py`  
> Roda via `docker exec -u root wms-superset python3 /tmp/superset_docker_setup.py` (após `docker cp`)

---

## Agentes IA

Stack: **CrewAI** + **Claude (Anthropic API)** + PostgreSQL gold + Qdrant RAG

### Arquitetura dos Agentes

```
Pergunta do usuário
       │
       ▼
┌─────────────────────┐
│   WMS Data Analyst  │  ← Claude via Anthropic API
│   (AnalystAgent)    │    Executa SQL no schema gold
└────────┬────────────┘
         │ dados quantitativos
         ▼
┌──────────────────────────┐
│ WMS Operations Researcher│  ← Claude via Anthropic API
│   (ResearchAgent)        │    Busca semântica no Qdrant
└────────┬─────────────────┘    (runbooks, ADRs, incidentes)
         │ contexto operacional
         ▼
┌──────────────────────────┐
│  WMS Operations Reporter │  ← Claude via Anthropic API
│   (ReporterAgent)        │    Síntese executiva em Markdown
└────────┬─────────────────┘
         │ resposta final
         ▼
     FastAPI /chat/stream (SSE)
```

### Agentes

| Agente | Nome no CrewAI | Arquivo | Função |
|---|---|---|---|
| `AnalystAgent` | WMS Data Analyst | `app/agents/analyst_agent.py` | Identifica marts relevantes, gera e executa SQL no schema gold, interpreta resultados |
| `ResearchAgent` | WMS Operations Researcher | `app/agents/research_agent.py` | Busca semântica no Qdrant por runbooks, ADRs e incidentes passados relacionados à pergunta |
| `ReporterAgent` | WMS Operations Reporter | `app/agents/reporter_agent.py` | Sintetiza dados quantitativos + contexto operacional em resposta estruturada (Resumo Executivo · Dados Chave · Contexto · Recomendações) |
| `WMSCrew` | crew | `app/agents/wms_crew.py` | Orquestra os três agentes em sequência via CrewAI |

### LLM e Embeddings

| Componente | Modelo | Provedor |
|---|---|---|
| LLM dos agentes | Claude (Anthropic API) | Anthropic — configurar `ANTHROPIC_API_KEY` |
| Embeddings Qdrant | `BAAI/bge-base-en-v1.5` (768 dims) | FastEmbed — local, sem custo |
| Memória CrewAI (Chroma) | `text-embedding-3-small` | OpenAI — requer `OPENAI_API_KEY` |

> **Nota:** A memória entre sessões (Chroma) usa embeddings da OpenAI. Para rodar sem `OPENAI_API_KEY`, o `WMSCrew` detecta automaticamente a ausência da variável e inicializa com `memory=False`.

### Qdrant — Knowledge Base

Coleção `wms_operational_docs` — modelo `BAAI/bge-base-en-v1.5` (768 dims, FastEmbed).

Indexar documentos:
```bash
python3 pipelines/rag/embed_docs.py \
  --docs-dir docs \
  --qdrant-url http://localhost:6333
```

Conteúdo indexado: ADRs de arquitetura, runbooks de recuperação de pipeline, documentação técnica da plataforma.

### Ferramentas dos Agentes

| Tool | Agente | Descrição |
|---|---|---|
| `wms_sql_analyst` | AnalystAgent | Executa queries SQL no PostgreSQL schema gold |
| `wms_operational_knowledge_search` | ResearchAgent | Busca semântica vetorial no Qdrant |
| `search_memory` | Todos | Recupera contexto da memória compartilhada (Chroma) |

### Perguntas de exemplo

- "Qual a saúde geral do estoque por armazém?"
- "Quais empresas têm mais pedidos atrasados este mês?"
- "Qual o desempenho dos operadores esta semana?"
- "Qual o tamanho da base gold?"
- "Como recuperar o pipeline em caso de falha do dbt?"

---

## Observabilidade

### LangFuse — Tracing de LLM (self-hosted)

Cada execução do crew é rastreada automaticamente no LangFuse local (`http://localhost:3001`).

**O que é capturado por run:**
- Trace completo da crew com input (pergunta) e output (resposta final)
- Span da execução do crew e geração-resumo da resposta final
- Tokens consumidos, status da execução e metadados de cada task
- Metadados: task outputs, session ID, tags `crewai` e `wms`

**Arquitetura de instrumentação:**

| Componente | Arquivo | Função |
|---|---|---|
| `observability.py` | `app/agents/observability.py` | Singleton LangFuse + `trace_crew_run()` context manager |
| `wms_crew.py` | `app/agents/wms_crew.py` | Envolve cada `run_wms_crew()` com `trace_crew_run()` |
| Agentes | `analyst_agent.py`, `research_agent.py`, `reporter_agent.py` | LLMs CrewAI sem `CallbackHandler`; tracing é feito no nível do crew para evitar incompatibilidade CrewAI/LiteLLM |

O LangFuse pode ser desabilitado sem alterar código via `LANGFUSE_ENABLED=false` no `.env`.

### DeepEval — Avaliação de Qualidade

Suite de evals em `app/evals/test_crew_quality.py` para medir a qualidade das respostas do crew.

**Métricas:**

| Métrica | Threshold | O que mede |
|---|---|---|
| `AnswerRelevancyMetric` | ≥ 0.7 | A resposta é relevante para a pergunta? |
| `FaithfulnessMetric` | ≥ 0.7 | A resposta é fiel ao contexto retornado pelo SQL? |
| `BiasMetric` | ≤ 0.5 | A resposta contém viés injustificado? |

**Como rodar:**

```bash
# Rodar suite completa dentro do container da API
docker exec wms-api pytest app/evals/ -v --timeout=300
```

Os resultados são publicados no LangFuse como scores ligados ao trace da execução.
Se o provedor do juiz DeepEval falhar por quota/configuração, o erro também é
registrado como score `*_error` para não ficar invisível no dashboard.

---

## Orquestração Airflow

6 DAGs com ordem de execução:

```
dag_extract_wms       → 01h  — extração Oracle → bronze
dag_transform_dbt     → 03h  — dbt run (silver + gold)
dag_quality_check     → 04h  — testes dbt
dag_embed_rag         → semanal — re-indexa docs no Qdrant
dag_freshness_monitor → horário — alerta de frescor dos dados
dag_enrich_geo        → semanal (seg 03h) — ViaCEP + IBGE + Open-Meteo → geo_reference + weather_daily
```

> Para rodar o dbt manualmente sem Airflow: `docker exec wms-airflow-webserver bash -c "dbt run --full-refresh --project-dir /opt/airflow/dbt_wms --profiles-dir /opt/airflow/dbt_wms"`

---

## Infraestrutura como Código

Toda a infraestrutura local é definida declarativamente — sem provisionamento manual.

| Arquivo | O que define |
|---|---|
| `docker-compose.yml` | 7 serviços: PostgreSQL, Airflow, Grafana, Superset, FastAPI, Qdrant, LangFuse |
| `docker/postgres/init.sql` | Schemas `bronze`, `silver`, `gold` e tabelas de controle |
| `docker/grafana/provisioning/` | Datasources e providers de dashboard (auto-provisionados) |
| `docker/grafana/dashboards/*.json` | 3 dashboards Grafana versionados em JSON |
| `transform/dbt_wms/profiles.yml` | Conexão dbt → PostgreSQL local |
| `.env.example` | Template de variáveis de ambiente |
| `Makefile` | Comandos reproduzíveis: `make dev`, `make extract`, `make dbt-run` |

Subir o ambiente completo do zero:

```bash
cp .env.example .env   # preencha as credenciais
docker compose up -d   # toda a stack em ~60s
```

---

## Estrutura do Repositório

```
docker/
  postgres/
    init.sql              # cria schemas bronze, silver, gold e tabelas
  grafana/
    dashboards/
      wms_operations.json # dashboard operacional WMS (15 painéis, range 30d)
      wms_pipeline.json   # monitoramento Airflow + ETL (13 painéis)
      wms_geo.json        # mapa geográfico SLA + clima (7 painéis)
    provisioning/
      datasources/
        postgres.yml          # datasource WMS PostgreSQL
        airflow_postgres.yml  # datasource Airflow PostgreSQL

scripts/
  superset_docker_setup.py  # reconstrói Superset do zero: 13 charts + dashboard

transform/dbt_wms/
  models/staging/         # 3 views (stg_orders, stg_inventory, stg_movements)
  models/marts/           # 8 marts analíticos gold
  macros/compat.sql       # wms_epoch, wms_hour, wms_today (cross-db)
  profiles.yml            # target local (PostgreSQL)

app/
  agents/                 # AnalystAgent, ResearchAgent, ReporterAgent, WMSCrew
  api/                    # FastAPI: main, routes, schemas, services
  requirements.txt
  Dockerfile

pipelines/
  extraction/
    oracle_to_postgres.py # extrai Oracle → bronze (watermark + snapshot)
  rag/
    embed_docs.py         # indexa docs/ no Qdrant (BAAI/bge-base-en-v1.5)
  dags/                   # 6 DAGs Airflow
  gold/                   # scripts auxiliares de geração gold

docs/
  adr/                    # ADRs de arquitetura e decisões técnicas
  runbooks/               # pipeline-recovery.md
  architecture.md

docker-compose.yml
Dockerfile.airflow
Makefile
.env.example
```

---

## Status

```
✅ CONCLUÍDO
──────────────────────────────────────────────────────────────
✅ Docker Compose — PostgreSQL, Qdrant, Airflow, Grafana,
                    Superset, FastAPI
✅ Bronze — init.sql, extração watermark Oracle (1 ano de dados reais)
✅ Silver — 7 modelos dbt (staging views + fct + dim)
✅ Gold — 8 marts analíticos, dbt cross-db compat
✅ Grafana — 3 dashboards (Operações · Pipeline/Airflow · Mapa Geográfico)
✅ Superset — 13 charts, dashboard reconstruído via script
✅ Agentes IA — AnalystAgent + ResearchAgent + ReporterAgent (end-to-end)
✅ RAG — 89 chunks indexados (ADRs, runbooks, contratos operacionais)
✅ API FastAPI — rota /chat + HTML chat UI
✅ Frontend React — ChatInterface com streaming SSE + cards de métricas
✅ Enriquecimento geográfico — DAG semanal via ViaCEP + IBGE + Open-Meteo,
                               tabelas geo_reference e weather_daily,
                               JOINs nos marts geo/weather
✅ DAGs Airflow — 6 DAGs implementadas com lógica completa
✅ CI/CD — 9 GitHub Actions workflows (lint, dbt compile, deploy, security scan)
✅ Observabilidade — LangFuse self-hosted (traces, tokens, outputs e scores DeepEval)
```

---

## Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Banco de dados | PostgreSQL 16 (bronze / silver / gold) |
| Transformação | dbt Core 1.10 + dbt-postgres |
| LLM | Claude (Anthropic API) |
| Orquestração de agentes | CrewAI |
| RAG / memória semântica | Qdrant v1.9 + FastEmbed |
| Vector store | Qdrant v1.9 |
| API | FastAPI + Uvicorn |
| Orquestração | Apache Airflow 2 (LocalExecutor) |
| Dashboards | Grafana + Apache Superset |
| Observabilidade LLM | LangFuse |
| Avaliação | DeepEval |
| Infra local | Docker Compose |

---

## Comandos Úteis

```bash
# Stack
docker compose up -d          # sobe todos os serviços
docker compose down           # para e remove containers
docker compose logs -f        # acompanha logs

# Extração e transformação
make extract-full             # extração full Oracle → bronze
make extract                  # extração incremental
make dbt-run                  # dbt run sobre bronze atual
make pipeline-real            # clean-bronze + extract-full + dbt-run
docker exec wms-airflow-webserver bash -c \
  "dbt run --full-refresh --project-dir /opt/airflow/dbt_wms \
            --profiles-dir /opt/airflow/dbt_wms"

# Superset — reconstrói dashboard do zero
docker cp scripts/superset_docker_setup.py wms-superset:/tmp/
docker exec -u root wms-superset python3 /tmp/superset_docker_setup.py

# RAG — reindexação limpa no Qdrant local
docker compose run --rm -v "$PWD:/workspace" api python pipelines/rag/embed_docs.py \
  --docs-dir docs \
  --qdrant-url http://qdrant:6333
```
