# WMS Data Platform — Arquitetura Completa

> Plataforma de dados moderna construída sobre Oracle WMS — cobrindo o ciclo completo
> de engenharia de dados: extração incremental, arquitetura medallion (bronze/silver/gold)
> em PostgreSQL, transformações dbt, orquestração Airflow, enriquecimento geográfico
> via APIs públicas e camada de AI conversacional com agentes autônomos.

---

## Diagrama Geral

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SOURCE LAYER                                    │
│                    Oracle WMS  (read-only)                               │
│         orders · inventory · movements · tasks · operators               │
│                     master data · locations                              │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                          extração incremental
                          (cx_Oracle + checkpoint)
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                                  │
│              Apache Airflow — Docker local (porta 8080)                 │
│                                                                          │
│  DAG 1: extract_master   (diário 01h)                                   │
│  DAG 2: transform_dbt    (diário 03h)                                   │
│  DAG 3: quality_check    (diário 04h)                                   │
│  DAG 4: enrich_apis      (diário 02h30)                                 │
│  DAG 5: embed_rag        (semanal)                                      │
│  DAG 6: freshness_check  (horário)                                      │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ENRICHMENT LAYER                                     │
│                    Python scripts — Airflow tasks                        │
│                                                                          │
│   ViaCEP         →  CEP → cidade, estado, bairro, lat/long              │
│   IBGE API       →  código cidade → população, região                   │
│   Open-Meteo     →  data + cidade → clima histórico                     │
│   ANTT           →  arquivo estático → dados de transportadoras         │
│                                                                          │
│   Resultados persistidos em bronze.geo_reference e bronze.weather_daily │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              DATA LAKE — PostgreSQL (bronze / silver / gold)            │
│                                                                          │
│   bronze/    raw Oracle + enriquecimento bruto (sem transformação)      │
│              registros preservados com metadados de ingestão            │
│                                                                          │
│   silver/    normalizado · dedupado · tipado · enriquecido              │
│              endereços geocodificados · clima integrado                  │
│                                                                          │
│   gold/      agregados · marts analíticos · dimensão geográfica         │
│                                                                          │
│   Contratos explícitos entre camadas · rastreabilidade ponta a ponta    │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              TRANSFORMATION LAYER — dbt Core + dbt-postgres             │
│                                                                          │
│   staging/        1:1 com tabelas Oracle (limpeza, tipos, nulos)        │
│   intermediate/   joins · regras de negócio WMS · cálculos              │
│   marts/          agregações finais prontas para consumo                 │
│                                                                          │
│   mart_picking_performance    produtividade por operador, turno         │
│   mart_inventory_health       giro, cobertura, risco de ruptura         │
│   mart_order_sla              tempo de ciclo, aderência ao prazo        │
│   mart_operator_productivity  ranking com contexto de complexidade      │
│   mart_stockout_risk          projeção de ruptura por SKU               │
│   mart_geo_performance        SLA por estado/cidade (choropleth)        │
│   mart_geo_inventory          cobertura de estoque por região           │
│   mart_weather_impact         correlação atraso x clima                 │
│                                                                          │
│   testes automáticos: not_null · unique · accepted_values               │
│                        relationships · freshness · volume anomaly       │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               SERVING — PostgreSQL gold schema                          │
│                                                                          │
│   Schemas: bronze · silver · gold                                       │
│   Conexão via psycopg2 / asyncpg                                        │
│   Mesma instância PostgreSQL para toda a plataforma                     │
└──────────────────┬──────────────────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────┐   ┌─────────────────────────────────────────────────────┐
│   SERVING     │   │                   AI LAYER                          │
│   PostgreSQL  │   │                                                      │
│   gold schema │   │   Qdrant (local)  vetores — runbooks + docs          │
│   SQL direto  │   │                                                      │
│               │   │   Anthropic API   Claude (LLM)                      │
│               │   │                                                      │
│               │   │   AnalystAgent    SQL no gold PostgreSQL            │
│               │   │   ResearchAgent   RAG semântico no Qdrant           │
│               │   │   ReporterAgent   síntese executiva final           │
│               │   │                                                      │
│               │   │   LangFuse        rastreamento de todas as chamadas │
│               │   │   DeepEval        avaliação faithfulness/relevancy  │
└───────┬───────┘   └──────────────────────────┬──────────────────────────┘
        └──────────────────────┬───────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API LAYER                                        │
│                       FastAPI — uvicorn local                           │
│                       autenticação via API Key                          │
└─────────────────────────────┬───────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       INTERFACE LAYER                                    │
│                       React + Vite — servidor local                     │
│                                                                          │
│   ChatInterface          perguntas em linguagem natural                 │
│   InventoryDashboard     saúde do estoque em tempo real                 │
│   OperationsDashboard    KPIs operacionais do armazém                   │
│   GeoMap Dashboard       SLA e estoque por região (Grafana embed)       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Camada Transversal

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INFRAESTRUTURA LOCAL                              │
│                                                                          │
│   Docker Compose        orquestra todos os serviços locais              │
│   ├── wms-postgres      PostgreSQL 15 (bronze · silver · gold)          │
│   ├── wms-airflow       Airflow scheduler + webserver (porta 8080)      │
│   ├── wms-grafana       Grafana 10 (porta 3000)                         │
│   └── wms-qdrant        Qdrant vector store (porta 6333)                │
│                                                                          │
│   Volumes persistentes para PostgreSQL e Qdrant                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           CI/CD                                          │
│                      GitHub Actions                                      │
│                                                                          │
│   ci.yml              lint · testes · dbt compile                       │
│   dbt-run.yml         dbt run + test agendado diário                    │
│   security-scan.yml   bandit · trivy · gitleaks                         │
│                                                                          │
│   Branch strategy: feature/* → dev → main                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILIDADE                                   │
│                                                                          │
│   Grafana (local)     4 dashboards: executivo · pipeline · geo · qualidade│
│   LangFuse            rastreamento LLM: prompt · contexto · latência    │
│   DeepEval            avaliação agentes: faithfulness · relevancy       │
│   dbt artifacts       lineage graph · test results                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          SEGURANÇA                                       │
│                                                                          │
│   .env                credenciais isoladas, nunca commitadas            │
│   Pre-commit          gitleaks — zero secrets no código                 │
│   API Key             autenticação de acesso à FastAPI                  │
│   Conexão read-only   Oracle WMS acesso restrito                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Estrutura do Repositório

```
wms-data-platform/
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── dbt-run.yml
│       └── security-scan.yml
│
├── docker/
│   ├── grafana/
│   │   ├── dashboards/          ← JSONs dos dashboards provisionados
│   │   └── provisioning/        ← datasources e dashboard providers
│   └── airflow/
│
├── pipelines/
│   ├── dags/                    ← Airflow DAGs (6 DAGs)
│   │   ├── dag_extract_master.py
│   │   ├── dag_transform_dbt.py
│   │   ├── dag_quality_check.py
│   │   ├── dag_enrich_apis.py
│   │   ├── dag_embed_rag.py
│   │   └── dag_freshness_check.py
│   ├── extraction/
│   │   ├── oracle_connector.py
│   │   ├── checkpoint.py
│   │   ├── anonymizer.py
│   │   └── extractors/
│   │       ├── orders.py
│   │       ├── inventory.py
│   │       ├── movements.py
│   │       ├── tasks.py
│   │       ├── operators.py
│   │       └── master_data.py
│   └── enrichment/
│       ├── orchestrator.py
│       └── apis/
│           ├── viacep.py
│           ├── ibge.py
│           ├── open_meteo.py
│           └── antt.py
│
├── transform/
│   └── dbt_wms/
│       ├── dbt_project.yml
│       ├── profiles.yml              ← postgres target
│       ├── models/
│       │   ├── staging/
│       │   ├── intermediate/
│       │   └── marts/
│       │       ├── mart_picking_performance.sql
│       │       ├── mart_inventory_health.sql
│       │       ├── mart_order_sla.sql
│       │       ├── mart_operator_productivity.sql
│       │       ├── mart_stockout_risk.sql
│       │       ├── mart_geo_performance.sql
│       │       ├── mart_geo_inventory.sql
│       │       └── mart_weather_impact.sql
│       ├── tests/
│       ├── macros/
│       └── seeds/
│
├── app/
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── chat.py
│   │   │   ├── inventory.py
│   │   │   ├── operations.py
│   │   │   ├── geo.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── agent_service.py
│   │   │   ├── sql_service.py
│   │   │   └── rag_service.py
│   │   └── schemas/
│   └── agents/
│       ├── analyst_agent.py
│       ├── research_agent.py
│       └── reporter_agent.py
│
├── web/
│   └── src/
│       ├── components/
│       │   ├── ChatInterface.jsx
│       │   ├── InventoryDashboard.jsx
│       │   ├── OperationsDashboard.jsx
│       │   └── GeoMapDashboard.jsx
│       └── App.jsx
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── agents/
│
├── docs/
│   ├── architecture.md
│   ├── wms-data-platform-architecture.md
│   ├── data-model.md
│   ├── adr/
│   │   ├── 001-medallion-on-postgres.md
│   │   ├── 002-batch-over-cdc.md
│   │   ├── 003-dbt-postgres-serving.md
│   │   ├── 004-delivered-at-proxy.md
│   │   └── 005-geo-enrichment.md
│   ├── runbooks/
│   └── images/
│
├── .claude/
│   ├── agents/
│   ├── kb/
│   └── CLAUDE.md
│
├── .pre-commit-config.yaml
├── docker-compose.yml
├── Makefile
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Stack Tecnológico Resumido

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Orquestração | Apache Airflow (Docker local) |
| Ingestão batch | Python + cx_Oracle |
| Banco de dados | PostgreSQL 15 (bronze / silver / gold) |
| Formato de dados | tabelas PostgreSQL nativas |
| Transformação | dbt Core + dbt-postgres |
| Enriquecimento | Python + ViaCEP + IBGE + Open-Meteo + ANTT |
| Vetores | Qdrant (Docker local) |
| LLM | Claude via Anthropic API |
| Agentes | LangChain / CrewAI |
| API | FastAPI + uvicorn |
| Frontend | React + Vite |
| Mapas | Grafana Geomap (embed no React) |
| Dashboards | Grafana (Docker local, porta 3000) |
| CI/CD | GitHub Actions |
| Avaliação LLM | DeepEval + LangFuse |
| Dev local | Docker Compose + Pre-commit |

---

## Fluxo de Dados Completo

```
Oracle WMS
    │
    └─[batch]─► Airflow ──► Python extrator (cx_Oracle) ──► PostgreSQL bronze
                                                                     │
                              APIs Externas                          │
                    ViaCEP + IBGE + Open-Meteo + ANTT               │
                              │                                      │
                    Python enrichment scripts ───────────────────►──│
                                                                     │
                                                          dbt-postgres│
                                                                     ▼
                                                       PostgreSQL silver
                                                                     │
                                                          dbt-postgres│
                                                                     ▼
                                                        PostgreSQL gold
                                                       (8 marts analíticos)
                                                                     │
                                               ┌─────────────────────┤
                                               │                     │
                                          Agentes AI             Grafana
                                     AnalystAgent (SQL)          4 Dashboards
                                     ResearchAgent (RAG)         incl. Geomap
                                     ReporterAgent (síntese)
                                               │
                                          FastAPI
                                               │
                                       React Frontend
```

---

## ADRs — Decisões Arquiteturais Documentadas

| ADR | Decisão | Justificativa |
|---|---|---|
| 001 | Medallion no PostgreSQL em vez de data lake em arquivo | Portabilidade, zero infraestrutura de nuvem, contratos simples de schema |
| 002 | Extração batch com cx_Oracle em vez de CDC | Suficiente para o volume, sem dependência de infraestrutura de streaming |
| 003 | dbt-postgres para transformação e serving | Mesma engine para transformar e servir; sem serviços externos |
| 004 | Proxy de `delivered_at` via status de movimento | Oracle WMS não expõe data de entrega diretamente |
| 005 | Open-Meteo + ViaCEP para enriquecimento geográfico | APIs públicas gratuitas, sem necessidade de chave |

---

*Documento atualizado em 23/04/2026 — WMS Data Platform Portfolio Project*
