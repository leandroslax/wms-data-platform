# WMS Data Platform

Plataforma moderna de dados construída sobre Oracle WMS, cobrindo o ciclo completo de engenharia de dados: ingestão incremental, lakehouse medallion no S3, transformações com dbt no Glue, warehouse analítico no Redshift Serverless e camada de agentes de IA.

---

## Arquitetura

```
Oracle WMS
  ├─[CDC]──► DMS → Kinesis → Lambda Consumer ──► S3 Bronze (Parquet)
  └─[batch]─► Lambda (cx_Oracle) + checkpoint ──► S3 Bronze (Parquet)
                                                        │
                                          Glue Crawler → Glue Catalog
                                                        │
                                              dbt + Glue (Spark)
                                                        │
                                          S3 Silver (Parquet, Glue Catalog)
                                                        │
                                    ┌───────────────────┤
                               Redshift              Grafana Cloud
                              Serverless              4 dashboards
                                    │
                          AnalystAgent (SQL)
                          ResearchAgent (RAG)
                          ReporterAgent (síntese)
                                    │
                           FastAPI (Lambda + API Gateway)
                                    │
                          React + Vite (S3 + CloudFront)
```

### Camadas

| Camada | Localização | Tecnologia |
|---|---|---|
| Extração batch | `pipelines/extraction/` | Lambda + cx_Oracle, checkpoint em S3 |
| CDC | `pipelines/cdc/` | AWS DMS → Kinesis → consumer Lambda |
| Enriquecimento | `pipelines/enrichment/` | Lambda + SQS, ViaCEP / IBGE / INMET / ANTT |
| Data Lake Bronze | S3 + Glue Catalog | Parquet particionado por entidade |
| Transformações | `transform/dbt_wms/` | dbt Core no AWS Glue (Spark) |
| Data Lake Silver | S3 + Glue Catalog | Parquet, deduplicated, typed |
| Warehouse | Redshift Serverless | 8 marts analíticos + Redshift Spectrum |
| Agentes IA | `app/agents/` | LangChain / CrewAI, Claude Haiku via Bedrock, Qdrant RAG |
| API | `app/api/` | FastAPI no Lambda + API Gateway + WAF |
| Frontend | `web/` | React + Vite, S3 + CloudFront |
| Infraestrutura | `infra/terraform/` | 15 módulos Terraform |
| Orquestração | `pipelines/dags/` | Apache Airflow (Astronomer Cloud, 7 DAGs) |

---

## Status atual

### ✅ Concluído

**Fundação de infraestrutura**
- Terraform com remote state (S3 + DynamoDB lock)
- Buckets S3 com naming corporativo e KMS por camada
- IAM roles com least-privilege (Glue, Lambda, execução)
- ECR provisionado para imagens Lambda

**Ingestão Bronze**
- Extrator incremental Oracle WMS → S3 em Parquet (`export_oraint_parquet.py`)
- Suporte a modo `incremental` (watermark por PK) e `snapshot_full`
- Entidades extraídas: `orders_documento`, `inventory_produtoestoque`, `movements_entrada_saida`, `products_snapshot`
- Glue Crawler configurado sobre o bronze; tabelas registradas no Glue Catalog (`wms_bronze_prod`)

**Pipeline dbt — Silver**
- Staging views com colunas reais do Oracle WMS e deduplicação por chave de negócio (`ROW_NUMBER`)
- Mart tables materializados como Parquet no S3 silver via Glue (Spark)
- **19/19 testes de dados passando** (`not_null` + `unique` em todas as PKs)

Modelos ativos:

| Modelo | Tipo | Descrição |
|---|---|---|
| `stg_inventory` | view | Inventário normalizado de `inventory_produtoestoque` |
| `stg_movements` | view | Movimentações de `movements_entrada_saida` |
| `stg_orders` | view | Documentos de `orders_documento` |
| `fct_inventory_snapshot` | table | Posição de estoque por produto/armazém |
| `fct_movements` | table | Movimentações com delta de quantidade |
| `fct_orders` | table | Documentos de saída |
| `dim_products` | table | Dimensão produto deduplicated |

### 🔄 Em andamento / Próximos passos

1. **Terraform** — persistir políticas KMS (Decrypt + GenerateDataKey) no módulo IAM para sobreviver a `terraform apply`
2. **Redshift COPY** — carregar silver marts no Redshift Serverless para a camada de serving
3. **DAG Airflow** — agendar `dbt run` diário no Astronomer Cloud
4. **AnalystAgent** — LangChain + Redshift para Q&A em linguagem natural sobre os marts
5. **API FastAPI** — endpoints de serving analítico conectados ao Redshift
6. **Grafana** — dashboards operacionais sobre os marts silver/gold

---

## Stack

- **Linguagem:** Python 3.11+
- **IaC:** Terraform (15 módulos, remote state, ambientes `dev` / `prod`)
- **Data Lake:** Apache Parquet + AWS Glue Data Catalog
- **Transformações:** dbt Core 1.10 + dbt-glue 1.10 (Spark no Glue)
- **Warehouse:** Redshift Serverless
- **Agentes:** LangChain / CrewAI, Claude Haiku (Bedrock), Qdrant, LangFuse, DeepEval
- **API:** FastAPI + Lambda + API Gateway + WAF
- **Frontend:** React + Vite + S3 + CloudFront
- **Segurança:** KMS (3 chaves), GuardDuty, CloudTrail, WAF, Secrets Manager, IAM least-privilege
- **Observabilidade:** CloudWatch (6 log groups, 8 alarmes), Grafana Cloud, LangFuse, DeepEval, AWS Budgets
- **CI/CD:** GitHub Actions (7 workflows: ci, infra, lambda, frontend, dbt, security, docs)

---

## Estrutura do projeto

```
infra/terraform/          # fundação AWS, segurança, rede, compute, monitoring
pipelines/
  extraction/             # extratores Oracle → S3 Bronze
  cdc/                    # Kinesis consumer
  enrichment/             # enriquecimento geográfico e climático
  dags/                   # DAGs Airflow
transform/dbt_wms/        # projeto dbt (staging → marts)
app/
  api/                    # FastAPI
  agents/                 # AnalystAgent, ResearchAgent, ReporterAgent
web/                      # React + Vite
docs/                     # arquitetura, ADRs, runbooks, contratos
.claude/                  # KB, agents, comandos, memória de trabalho
```

---

## Buckets S3

| Bucket | Finalidade |
|---|---|
| `wms-dp-{env}-bronze-us-east-1-896159010925` | Dados brutos Oracle + CDC |
| `wms-dp-{env}-silver-us-east-1-896159010925` | Dados normalizados, deduplicados, tipados |
| `wms-dp-{env}-gold-us-east-1-896159010925` | Marts agregados prontos para consumo |
| `wms-dp-{env}-artifacts-us-east-1-896159010925` | Checkpoints, cache, artefatos dbt |
| `wms-dp-{env}-query-results-us-east-1-896159010925` | Resultados de queries (lifecycle 7 dias) |
| `wms-dp-{env}-frontend-us-east-1-896159010925` | Build React (CloudFront OAC) |
| `wms-data-platform-tf-state-896159010925` | Terraform remote state |

---

## Documentação

- `docs/architecture.md`
- `docs/source-system-contract.md`
- `docs/bronze-contract.md`
- `docs/silver-contract.md`
- `docs/serving-strategy.md`
- `docs/api-serving-integration.md`
- `docs/redshift-query-contract.md`
