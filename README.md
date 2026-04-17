# WMS Data Platform

Plataforma de dados moderna para Oracle WMS, desenhada para demonstrar engenharia de dados ponta a ponta em AWS.

O projeto combina ingestao batch e CDC, lakehouse com Apache Iceberg no S3, Glue Catalog, transformacoes com dbt + Glue, serving analitico com Redshift Serverless e uma camada de AI conversacional com agentes especializados.

## Objetivo

Este repositorio foi pensado como projeto de portfolio com foco em arquitetura realista, boas praticas de cloud, seguranca, observabilidade e AI aplicada a analytics operacional.

A ideia central e responder perguntas como:

- como estruturar um pipeline WMS moderno em AWS?
- como sair de Oracle operacional para lakehouse + warehouse analitico?
- como usar runbooks e documentacao como memoria semantica para agentes?
- como entregar um projeto que pareca proximo de um ambiente real de engenharia de dados?

## Arquitetura Escolhida

Stack principal do projeto:

- `Oracle WMS` como sistema de origem
- `S3 + Apache Iceberg` como lakehouse em camadas `bronze`, `silver` e `gold`, com naming corporativo por ambiente, regiao e conta
- `AWS Glue Catalog` como catalogo das tabelas Iceberg
- `dbt + AWS Glue (Spark)` para transformacoes
- `Redshift Serverless` para serving analitico e consultas de produto
- `FastAPI` como camada de servico
- `Qdrant` como memoria vetorial para runbooks e documentacao
- `LangChain/CrewAI` para agentes
- `Airflow` para orquestracao
- `Terraform` para infraestrutura como codigo

## Fluxo de Dados

```text
Oracle WMS
  -> extracao batch e CDC
  -> S3 Bronze (Iceberg)
  -> dbt + Glue
  -> S3 Silver (Iceberg)
  -> dbt + Glue
  -> S3 Gold (Iceberg)
  -> Redshift Serverless
  -> API / dashboards / agentes
```

Camada semantica:

```text
docs/runbooks + ADRs + documentacao tecnica
  -> embeddings
  -> Qdrant
  -> ResearchAgent
  -> ReporterAgent
```

## Agentes

O projeto usa uma biblioteca de agents herdada da base `semana-ai-data-engineer`, mas com contexto de dominio proprio para WMS.

Agentes principais do produto:

- `AnalystAgent`: consultas SQL e metricas exatas sobre marts e views analiticas
- `ResearchAgent`: recuperacao semantica sobre runbooks, ADRs, incidentes e docs
- `ReporterAgent`: sintese final combinando contexto estruturado e semantico
- `wms-platform-builder`: agente de dominio para scaffolding e implementacao do projeto

## Decisoes Arquiteturais Principais

- `Iceberg` como formato de tabela oficial do lakehouse
- `Glue Catalog` como catalogo central das tabelas
- `Glue (Spark)` como engine principal de transformacao
- `Redshift Serverless` como camada de serving
- `Terraform` com ambientes `dev` e `prod`
- `Lambda` para componentes serverless do produto e ingestao

ADRs atuais:

- [ADR 001](docs/adr/001-delta-lake-vs-parquet.md)
- [ADR 002](docs/adr/002-glue-vs-redshift-transform.md)
- [ADR 003](docs/adr/003-serverless-vs-ec2.md)

## Estrutura do Repositorio

```text
.
├── .github/workflows/          # CI/CD, seguranca, docs, deploys
├── infra/terraform/            # modulos e ambientes AWS
├── pipelines/                  # DAGs, extractors, handlers e checkpoints
├── transform/dbt_wms/          # projeto dbt
├── app/api/                    # FastAPI
├── app/agents/                 # agentes de dominio
├── tests/                      # unit, integration, api, agents
├── docs/                       # arquitetura, ADRs, runbooks, imagens
├── .claude/                    # KB, agents, comandos e contexto local
├── docker-compose.yml          # ambiente local
├── devcontainer.json           # dev container para VS Code
├── Makefile
├── requirements.txt
└── .env.example
```

## Estado Atual

O repositorio esta em fase de scaffold, mas ja contem uma base coerente para evolucao:

- estrutura de pastas alinhada a arquitetura
- primeira leva de modulos Terraform essenciais
- base de API FastAPI
- placeholders de pipelines e agentes
- KB WMS para uso com Claude
- workflows iniciais de CI/CD
- documentacao arquitetural e ADRs

O que ja esta criado:

- modulos Terraform iniciais para `iam`, `s3`, `secrets`, `lambda` e `monitoring`
- ambientes `dev` e `prod`
- `README`, `CLAUDE.md`, KB WMS e ADRs
- API minima com endpoint `/health`

## Bootstrap na AWS

Como a conta AWS ja foi criada, o proximo passo pratico e preparar o backend remoto do Terraform.

### 1. Configurar credenciais AWS

```bash
aws configure
```

Sugestao:

- region: `us-east-1`
- output: `json`

### 2. Criar recursos do backend remoto

O backend do Terraform nao se cria sozinho. Antes do primeiro `terraform init`, voce precisa criar:

- bucket `wms-data-platform-tf-state-896159010925`
- tabela DynamoDB `wms-tf-locks`

### 3. Inicializar o ambiente `dev`

```bash
cd infra/terraform/envs/dev
terraform init
terraform plan
```

## Desenvolvimento Local

### Setup inicial

```bash
make setup
```

### Comandos principais

```bash
make lint
make test
make api-dev
make tf-plan
make tf-apply
```

## Data Model

Resumo atual:

### Bronze

- `bronze_orders`
- `bronze_inventory`
- `bronze_movements`
- `bronze_tasks`
- `bronze_operators`
- `bronze_master_data`

### Silver

- `silver_orders`
- `silver_inventory_snapshot`
- `silver_movements`
- `silver_tasks`
- `silver_operator_activity`
- `silver_locations_geo`

### Gold

- `mart_picking_performance`
- `mart_inventory_health`
- `mart_order_sla`
- `mart_operator_productivity`
- `mart_stockout_risk`
- `mart_geo_performance`
- `mart_geo_inventory`
- `mart_weather_impact`

## Observabilidade e Seguranca

Camadas planejadas:

- `CloudWatch` para logs, metricas, alarms e dashboard
- `SNS` para alertas
- `LangFuse` para observabilidade da camada de AI
- `DeepEval` para avaliacao dos agentes
- `KMS`, `Secrets Manager`, `WAF`, `CloudTrail`, `GuardDuty` e `AWS Config`

## Roadmap

### Fase 1

- bootstrap AWS
- backend remoto do Terraform
- modulos base de infra

### Fase 2

- extractor Oracle e checkpoint incremental
- primeiro dataset em bronze
- Glue Catalog e primeiros jobs

### Fase 3

- modelos dbt `staging`, `intermediate` e `marts`
- serving no Redshift Serverless
- API operacional inicial

### Fase 4

- ResearchAgent + Qdrant
- ReporterAgent
- avaliacao com DeepEval e tracing com LangFuse

## Documentacao Complementar

- [Arquitetura completa](docs/architecture.md)
- [Modelo de dados](docs/data-model.md)
- [Runbook inicial](docs/runbooks/pipeline-recovery.md)

## Observacao

Este projeto esta sendo construído com foco em clareza arquitetural e qualidade de demonstracao tecnica. O objetivo nao e apenas "funcionar", mas mostrar criterio de engenharia nas decisoes de plataforma, dados, seguranca e AI.
