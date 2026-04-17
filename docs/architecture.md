# WMS Data Platform — Arquitetura Completa

> Plataforma de dados moderna construída sobre Oracle WMS — cobrindo o ciclo completo
> de engenharia de dados: CDC em tempo real, arquitetura medallion Iceberg no S3,
> transformações dbt com Glue, orquestração Airflow, enriquecimento geográfico via APIs públicas,
> warehouse Redshift Serverless e camada de AI conversacional com agentes autônomos.

---

## Diagrama Geral

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SOURCE LAYER                                    │
│                    Oracle WMS  (read-only)                               │
│         orders · inventory · movements · tasks · operators               │
│                     master data · locations                              │
└───────────────────┬─────────────────────────┬───────────────────────────┘
                    │                         │
          tabelas transacionais          master data
          (alta mutabilidade)            (baixa mutabilidade)
                    │                         │
                    ▼                         ▼
┌───────────────────────────┐   ┌─────────────────────────────────────────┐
│   CDC LAYER               │   │         ORCHESTRATION LAYER              │
│   AWS DMS  (t3.micro)     │   │   Apache Airflow — Astronomer Cloud      │
│   lê Oracle redo log      │   │                (free tier)               │
│   captura INSERT/UPDATE/  │   │                                          │
│   DELETE continuamente    │   │  DAG 1: extract_master   (diário 01h)   │
│          ↓                │   │  DAG 2: transform_dbt    (diário 03h)   │
│   Kinesis Data Stream     │   │  DAG 3: quality_check    (diário 04h)   │
│   (1 shard — free tier)   │   │  DAG 4: load_warehouse   (diário 04h30) │
│          ↓                │   │  DAG 5: enrich_apis      (diário 02h30) │
│   Lambda CDC Consumer     │   │  DAG 6: embed_rag        (semanal)      │
└───────────┬───────────────┘   │  DAG 7: freshness_check  (horário)      │
            │                   └──────────────┬──────────────────────────┘
            │                                  │
            │                    ┌─────────────▼──────────────────────────┐
            │                    │         INGESTION LAYER                 │
            │                    │    AWS Lambda  (batch extractor)        │
            │                    │    Python + cx_Oracle                   │
            │                    │    checkpoint incremental no S3         │
            │                    └─────────────┬──────────────────────────┘
            │                                  │
            └──────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ENRICHMENT LAYER                                     │
│              Lambda Orchestrator → SQS → Lambda por API                 │
│                                                                          │
│   ViaCEP         →  CEP → cidade, estado, bairro, lat/long              │
│   IBGE API       →  código cidade → população, região, PIB              │
│   INMET          →  data + cidade → clima histórico                     │
│   ANTT           →  arquivo estático → dados de transportadoras         │
│                                                                          │
│   S3 Cache: respostas salvas por chave (CEP, código, data)              │
│   SQS DLQ: falhas de API vão para Dead Letter Queue + CloudWatch alarm  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               DATA LAKE — Amazon S3 + Apache Iceberg                    │
│                                                                          │
│   bronze/    raw Oracle + CDC events (sem transformação)                │
│              INSERT / UPDATE / DELETE preservados                        │
│                                                                          │
│   silver/    normalizado · dedupado · tipado · enriquecido              │
│              endereços geocodificados · clima integrado                  │
│                                                                          │
│   gold/      agregados · marts analíticos · dimensão geográfica         │
│                                                                          │
│   ACID Transactions · Time Travel · Schema Evolution                    │
│   Partition Evolution · Row-level Deletes · Glue Data Catalog           │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              TRANSFORMATION LAYER — dbt Core + AWS Glue (Spark)            │
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
│              DATA WAREHOUSE — Amazon Redshift Serverless                │
│                                                                          │
│   Namespace + Workgroup em VPC privada                                  │
│   IAM role para COPY do S3 e Spectrum                                   │
│   Schemas: staging · marts · geo                                        │
│   Redshift Spectrum: lê Iceberg gold direto do S3                       │
│   300 RPU-hours free trial                                               │
└──────────────────┬──────────────────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌───────────────┐   ┌─────────────────────────────────────────────────────┐
│   SERVING     │   │                   AI LAYER                          │
│   Redshift    │   │                                                      │
│   SQL direto  │   │   Qdrant Cloud    vetores — runbooks + docs          │
│               │   │                  (free tier permanente)              │
│               │   │                                                      │
│               │   │   Amazon Bedrock  Claude Haiku (LLM)                │
│               │   │                  ~R$0,01 por conversa               │
│               │   │                                                      │
│               │   │   AnalystAgent    SQL nos marts Redshift            │
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
│              FastAPI — AWS Lambda + API Gateway (REST)                  │
│              WAF Web ACL: SQL injection · XSS · rate limit              │
│              API Key para autenticação do frontend                      │
│              Throttling por endpoint · stages dev/prod                  │
└─────────────────────────────┬───────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       INTERFACE LAYER                                    │
│                React + Vite — S3 + CloudFront                           │
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
│                        INFRAESTRUTURA                                    │
│                                                                          │
│   Terraform          IaC — todos os recursos AWS como código            │
│   ├── modules/vpc                VPC · subnets · SGs · NAT Gateway      │
│   ├── modules/s3                 7 buckets + políticas + KMS            │
│   ├── modules/lambda             3 funções + ECR + layers               │
│   ├── modules/dms                instância + endpoints + task CDC       │
│   ├── modules/kinesis            stream + consumidor Lambda             │
│   ├── modules/sqs                filas de API + DLQ                     │
│   ├── modules/redshift           serverless namespace + workgroup       │
│   ├── modules/glue               jobs + Glue catalog               │
│   ├── modules/api_gateway        REST API + stages + WAF                │
│   ├── modules/cloudfront         distribuição + OAC + WAF               │
│   ├── modules/iam                1 role por serviço, least privilege    │
│   ├── modules/secrets            Secrets Manager + KMS keys             │
│   ├── modules/monitoring         CloudWatch + SNS + alarms              │
│   ├── modules/budget             alertas $50 · $100 · $150 · $200       │
│   ├── modules/cloudtrail         auditoria completa                     │
│   ├── modules/guardduty          detecção de ameaças                    │
│   └── modules/config             compliance contínuo                    │
│                                                                          │
│   Environments: dev · prod                                              │
│   Remote state: S3 + DynamoDB lock                                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           CI/CD                                          │
│                      GitHub Actions (7 workflows)                        │
│                                                                          │
│   ci.yml              lint · testes · dbt compile · tf validate         │
│   deploy-infra.yml    terraform plan (PR) + apply (merge)               │
│   deploy-lambda.yml   build Docker + push ECR + update função           │
│   deploy-frontend.yml build React + sync S3 + invalidar CloudFront      │
│   dbt-run.yml         dbt run + test agendado diário                    │
│   security-scan.yml   checkov · bandit · trivy · gitleaks               │
│   docs.yml            dbt docs + API docs → deploy S3                   │
│                                                                          │
│   Branch strategy: feature/* → dev → main                              │
│   Deploy prod: aprovação manual obrigatória                             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILIDADE                                   │
│                                                                          │
│   CloudWatch          logs · métricas · alarms · dashboard unificado   │
│   SNS                 alertas por email (erros Lambda, SLA, DLQ)        │
│   Grafana Cloud       4 dashboards: executivo · pipeline · geo · qualidade│
│   LangFuse            rastreamento LLM: prompt · contexto · latência    │
│   DeepEval            avaliação agentes: faithfulness · relevancy       │
│   dbt artifacts       lineage graph · test results → S3                 │
│   AWS Budgets         alertas de custo em 4 níveis                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          SEGURANÇA                                       │
│                                                                          │
│   Secrets Manager     Oracle creds · API keys · Bedrock key             │
│   KMS (3 keys)        S3 data · Redshift · Lambda env vars              │
│   IAM least privilege 1 role por serviço, zero permissões extras        │
│   VPC privada         Lambda extrator · Redshift · DMS em subnet privada│
│   VPC Endpoints       S3 · Secrets Manager (tráfego interno)            │
│   WAF                 API Gateway + CloudFront                          │
│   CloudTrail          log de toda ação na conta AWS                     │
│   GuardDuty           detecção de ameaças ativa                         │
│   AWS Config          compliance contínuo de todos os recursos          │
│   S3 Block Public     todos os buckets de dados bloqueados              │
│   Pre-commit          gitleaks — zero secrets no código                 │
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
│       ├── deploy-infra.yml
│       ├── deploy-lambda.yml
│       ├── deploy-frontend.yml
│       ├── dbt-run.yml
│       ├── security-scan.yml
│       └── docs.yml
│
├── infra/
│   └── terraform/
│       ├── modules/
│       │   ├── vpc/
│       │   ├── s3/
│       │   ├── lambda/
│       │   ├── dms/                  ← CDC
│       │   ├── kinesis/              ← streaming CDC
│       │   ├── sqs/                  ← filas API enrichment
│       │   ├── redshift/
│       │   ├── glue/
│       │   ├── api_gateway/
│       │   ├── cloudfront/
│       │   ├── waf/
│       │   ├── iam/
│       │   ├── secrets/
│       │   ├── monitoring/
│       │   ├── budget/
│       │   ├── cloudtrail/
│       │   ├── guardduty/
│       │   └── config/
│       ├── envs/
│       │   ├── dev/
│       │   └── prod/
│       └── backend/
│           └── state.tf              ← S3 + DynamoDB lock
│
├── pipelines/
│   ├── dags/                         ← Airflow (Astronomer Cloud)
│   │   ├── dag_extract_master.py
│   │   ├── dag_transform_dbt.py
│   │   ├── dag_quality_check.py
│   │   ├── dag_load_warehouse.py
│   │   ├── dag_enrich_apis.py
│   │   ├── dag_embed_rag.py
│   │   └── dag_freshness_check.py
│   ├── extraction/
│   │   ├── oracle_connector.py
│   │   ├── checkpoint.py
│   │   ├── anonymizer.py             ← mascaramento dados sensíveis
│   │   ├── parquet_writer.py
│   │   └── extractors/
│   │       ├── orders.py
│   │       ├── inventory.py
│   │       ├── movements.py
│   │       ├── tasks.py
│   │       ├── operators.py
│   │       └── master_data.py
│   ├── cdc/
│   │   └── kinesis_consumer.py       ← consome eventos DMS → S3 bronze
│   └── enrichment/
│       ├── orchestrator.py           ← publica para SQS
│       ├── cache.py                  ← S3 cache de respostas
│       ├── apis/
│       │   ├── viacep.py
│       │   ├── ibge.py
│       │   ├── inmet.py
│       │   └── antt.py
│       └── lambda_handlers/
│           ├── handler_viacep.py
│           ├── handler_ibge.py
│           └── handler_inmet.py
│
├── transform/
│   └── dbt_wms/
│       ├── dbt_project.yml
│       ├── profiles.yml              ← Glue + Redshift targets
│       ├── models/
│       │   ├── staging/
│       │   ├── intermediate/
│       │   └── marts/
│       │       ├── mart_picking_performance.sql
│       │       ├── mart_inventory_health.sql
│       │       ├── mart_order_sla.sql
│       │       ├── mart_operator_productivity.sql
│       │       ├── mart_stockout_risk.sql
│       │       ├── mart_geo_performance.sql    ← mapa SLA por região
│       │       ├── mart_geo_inventory.sql      ← mapa cobertura estoque
│       │       └── mart_weather_impact.sql     ← clima x atraso
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
│   │   │   ├── geo.py                ← endpoints geográficos
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── agent_service.py
│   │   │   ├── sql_service.py
│   │   │   └── rag_service.py
│   │   ├── schemas/
│   │   └── middleware/
│   └── agents/
│       ├── analyst_agent.py          ← SQL no Redshift
│       ├── research_agent.py         ← RAG no Qdrant
│       └── reporter_agent.py         ← síntese final
│
├── web/
│   └── src/
│       ├── components/
│       │   ├── ChatInterface.jsx
│       │   ├── InventoryDashboard.jsx
│       │   ├── OperationsDashboard.jsx
│       │   └── GeoMapDashboard.jsx   ← Grafana Geomap embed
│       └── App.jsx
│
├── tests/
│   ├── unit/                         ← pytest + moto (mock AWS)
│   ├── integration/
│   ├── api/
│   └── agents/                       ← DeepEval
│
├── docs/
│   ├── architecture.md               ← este documento
│   ├── data-model.md
│   ├── adr/
│   │   ├── 001-iceberg-vs-delta-lake.md
│   │   ├── 002-dms-cdc-vs-timestamp.md
│   │   ├── 002-glue-vs-redshift-transform.md
│   │   ├── 004-kafka-nao-utilizado.md ← decisão de NÃO usar Kafka
│   │   └── 005-serverless-vs-ec2.md
│   ├── runbooks/                     ← alimenta o RAG
│   └── images/
│
├── .claude/                          ← agents reutilizáveis
│   ├── agents/
│   ├── kb/
│   └── CLAUDE.md
│
├── .pre-commit-config.yaml           ← black · flake8 · isort · checkov · gitleaks
├── docker-compose.yml                ← ambiente local (Oracle XE + Airflow mock)
├── devcontainer.json
├── Makefile
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Inventário Completo de Recursos AWS

### Compute
| Recurso | Tipo | Custo |
|---|---|---|
| Lambda extrator | container 1GB 15min | free tier |
| Lambda CDC consumer | container 512MB | free tier |
| Lambda enrichment (3x) | container 256MB | free tier |
| Lambda API | container 512MB 30s | free tier |
| Lambda embedder | container 512MB 5min | free tier |
| DMS replication instance | t3.micro | free 12 meses |

### Storage
| Bucket | Uso | Config |
|---|---|---|
| `wms-dp-{env}-bronze-{region}-{account}` | raw + CDC events | Iceberg · KMS · versioning |
| `wms-dp-{env}-silver-{region}-{account}` | normalizado + enriquecido | Iceberg · KMS · versioning |
| `wms-dp-{env}-gold-{region}-{account}` | marts agregados | Iceberg · KMS · versioning |
| `wms-dp-{env}-artifacts-{region}-{account}` | checkpoints · cache API · dbt artifacts | KMS |
| `wms-dp-{env}-query-results-{region}-{account}` | resultados de queries e artefatos transitórios | lifecycle 7 dias |
| `wms-dp-{env}-frontend-{region}-{account}` | React build | privado via CloudFront OAC |
| `wms-data-platform-tf-state-896159010925` | Terraform remote state | versioning · MFA delete |

### Streaming & Mensageria
| Recurso | Uso | Custo |
|---|---|---|
| Kinesis Data Stream | eventos CDC do DMS | 1 shard free 12 meses |
| SQS ViaCEP queue | requisições geocoding | always free |
| SQS IBGE queue | requisições demografia | always free |
| SQS INMET queue | requisições clima | always free |
| SQS DLQ | falhas de API | always free |

### Analytics & Warehouse
| Recurso | Uso | Custo |
|---|---|---|
| Glue Jobs | dbt transformations over Iceberg | custo sob demanda |
| Glue Data Catalog | catálogo Iceberg | free 1M objects |
| Redshift Serverless | warehouse marts | 300 RPU-h trial |

### Rede & Segurança
| Recurso | Uso |
|---|---|
| VPC + subnets privadas | isolamento Lambda/DMS/Redshift |
| NAT Gateway | saída internet para Lambda privada |
| VPC Endpoints (S3, Secrets) | tráfego interno sem internet |
| Security Groups (3x) | Lambda · DMS · Redshift |
| Secrets Manager | Oracle creds · API keys · Bedrock |
| KMS (3 keys) | S3 data · Redshift · Lambda |
| WAF Web ACL | API Gateway + CloudFront |
| CloudTrail | auditoria completa |
| GuardDuty | detecção de ameaças |
| AWS Config | compliance contínuo |

### Observabilidade
| Recurso | Uso |
|---|---|
| CloudWatch Log Groups (6x) | 1 por Lambda + API GW |
| CloudWatch Alarms (8x) | erro Lambda · latência API · DLQ · frescor |
| CloudWatch Dashboard | visão unificada |
| SNS Topic | email em alarmes críticos |
| AWS Budgets | alertas $50 · $100 · $150 · $200 |

---

## Serviços Externos (fora AWS)

| Serviço | Uso | Custo |
|---|---|---|
| Astronomer Cloud | Airflow gerenciado | free tier |
| Qdrant Cloud | vector store RAG | free tier (1GB) |
| Grafana Cloud | dashboards + Geomap | free tier |
| LangFuse | observabilidade LLM | free tier |
| GitHub Actions | CI/CD | free (repo público) |
| ViaCEP | geocoding por CEP | gratuita |
| IBGE API | dados demográficos | gratuita |
| INMET | histórico climático | gratuita |
| ANTT | dados transportadoras | gratuita (arquivo) |

---

## Stack Tecnológico Resumido

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| Orquestração | Apache Airflow (Astronomer Cloud) |
| CDC | AWS DMS + Kinesis Data Streams |
| Ingestão batch | AWS Lambda + cx_Oracle |
| Formato de tabela | Apache Iceberg |
| Transformação | dbt Core + AWS Glue (Spark) |
| Warehouse | Amazon Redshift Serverless |
| Enriquecimento | Lambda + SQS + ViaCEP + IBGE + INMET + ANTT |
| Vetores | Qdrant Cloud |
| LLM | Amazon Bedrock (Claude Haiku) |
| Agentes | LangChain / CrewAI |
| API | FastAPI + API Gateway |
| Frontend | React + Vite + CloudFront |
| Mapas | Grafana Geomap (embed no React) |
| IaC | Terraform (15 módulos) |
| CI/CD | GitHub Actions (7 workflows) |
| Avaliação LLM | DeepEval + LangFuse |
| Segurança | WAF + KMS + GuardDuty + CloudTrail |
| Dev local | Docker Compose + Pre-commit |

---

## Fluxo de Dados Completo

```
Oracle WMS
    │
    ├─[CDC]──► DMS ──► Kinesis ──► Lambda Consumer ──► S3 Bronze (Iceberg)
    │                                                           │
    └─[batch]─► Airflow ──► Lambda Extrator ──────────────────►│
                                                                │
                              APIs Externas                     │
                    ViaCEP + IBGE + INMET + ANTT                │
                              │                                 │
                    Lambda Enrichment + SQS ──────────────────►│
                                                                │
                                                    dbt + Glue  │
                                                                ▼
                                                    S3 Silver (Iceberg)
                                                                │
                                                    dbt + Glue  │
                                                                ▼
                                                    S3 Gold (Iceberg)
                                                                │
                                                    Redshift COPY│
                                                                ▼
                                                  Redshift Serverless
                                                   (8 marts analíticos)
                                                                │
                                              ┌─────────────────┤
                                              │                 │
                                         Agentes AI         Grafana
                                    AnalystAgent (SQL)      4 Dashboards
                                    ResearchAgent (RAG)     incl. Geomap
                                    ReporterAgent (síntese)
                                              │
                                         FastAPI
                                    Lambda + API Gateway
                                              │
                                       React Frontend
                                      S3 + CloudFront
```

---

## ADRs — Decisões Arquiteturais Documentadas

| ADR | Decisão | Justificativa |
|---|---|---|
| 001 | Iceberg no lugar de Delta Lake | Integração nativa AWS: Glue Catalog, Glue Jobs e Redshift Spectrum |
| 002 | DMS CDC no lugar de extração por timestamp | Captura deletes, múltiplos updates, sem dependência de `updated_at` |
| 003 | Glue para transformação, Redshift para serving | Glue/Spark para dbt e Redshift otimizado para queries analíticas |
| 004 | Kafka não utilizado | Volume não justifica. Kinesis resolve com free tier e menor complexidade |
| 005 | Lambda no lugar de EC2/ECS | Custo zero em idle, escala automática, adequado ao volume de 8GB |

---

*Documento gerado em 17/04/2026 — WMS Data Platform Portfolio Project*
