# WMS Data Platform

## Visão geral
O WMS Data Platform é um projeto de engenharia de dados e IA aplicado a operações de warehouse management.

O objetivo é construir uma plataforma moderna de dados com:
- extração de dados de Oracle WMS
- lakehouse em S3 + Iceberg
- catálogo via Glue
- transformação com dbt
- serving analítico
- API FastAPI
- base futura para agentes analíticos

## Objetivo do projeto
Demonstrar uma arquitetura de dados moderna, profissional e explicável de ponta a ponta, cobrindo:

- ingestão
- contratos de dados
- governança de camadas
- serving analítico
- API
- observabilidade
- infraestrutura como código

## Escopo atual do MVP
O MVP está focado em 3 entidades principais:
- orders
- inventory
- movements

Essas entidades foram escolhidas por sustentarem melhor:
- operação
- analytics
- dashboards
- API
- futura camada de agentes

## Arquitetura resumida
Fluxo principal:

1. Oracle WMS como origem
2. extração incremental e snapshots
3. persistência em bronze
4. normalização em silver
5. transformação com dbt
6. serving analítico
7. consumo via API, dashboards e agentes

## Stack principal
- AWS S3
- Apache Iceberg
- AWS Glue Data Catalog
- dbt
- Redshift
- FastAPI
- Terraform
- GitHub Actions

## Estrutura principal do projeto
- `infra/terraform/`
- `pipelines/`
- `transform/dbt_wms/`
- `app/api/`
- `app/agents/`
- `tests/`
- `docs/`
- `.claude/`

## Camadas de dados

### Bronze
Responsável por:
- persistência bruta
- rastreabilidade
- replay
- auditoria

Bucket:
- `s3://wms-dp-dev-bronze-us-east-1-896159010925/`

### Silver
Responsável por:
- tipagem
- normalização
- deduplicação
- padronização

Entidades do MVP:
- `silver.orders`
- `silver.inventory`
- `silver.movements`

### Gold / Serving
Responsável por:
- fatos e dimensões analíticas
- serving para API
- base para dashboards e agentes

Modelos iniciais:
- `fct_orders`
- `fct_inventory_snapshot`
- `fct_movements`
- `dim_products`

## API do MVP
Endpoints disponíveis ou previstos:
- `/health`
- `/metadata`
- `/orders/summary`
- `/inventory/snapshot`
- `/movements/summary`

## Infraestrutura
A infraestrutura é provisionada com Terraform e hoje cobre principalmente:
- backend remoto com S3 + DynamoDB lock
- IAM
- KMS
- Secrets Manager
- buckets S3
- monitoring básico
- ECR

## Convenção de nomes
Os buckets seguem um padrão mais corporativo e globalmente único:

- `wms-dp-dev-bronze-us-east-1-896159010925`
- `wms-dp-dev-silver-us-east-1-896159010925`
- `wms-dp-dev-gold-us-east-1-896159010925`
- `wms-dp-dev-artifacts-us-east-1-896159010925`
- `wms-dp-dev-query-results-us-east-1-896159010925`
- `wms-dp-dev-frontend-us-east-1-896159010925`

Terraform backend:
- bucket: `wms-data-platform-tf-state-896159010925`
- dynamodb table: `wms-tf-locks`

## Status atual
Neste momento o projeto já possui:
- fundação Terraform funcional
- backend remoto do Terraform configurado
- bucket naming profissional
- ECR criado
- contratos documentados para source, bronze, silver e serving
- API MVP estruturada
- dbt inicial estruturado
- documentação arquitetural em evolução

## Documentação principal
- `docs/architecture.md`
- `docs/source-system-contract.md`
- `docs/entity-to-extractor-mapping.md`
- `docs/mvp-scope.md`
- `docs/mvp-extractors-spec.md`
- `docs/bronze-contract.md`
- `docs/checkpoint-strategy.md`
- `docs/silver-contract.md`
- `docs/serving-strategy.md`
- `docs/redshift-query-contract.md`
- `docs/redshift-adapter-plan.md`
- `docs/api-serving-integration.md`

## Próximos passos
1. estabilizar publicação da imagem da Lambda no ECR
2. concluir ativação da Lambda
3. alinhar extratores do MVP à documentação
4. conectar dbt à camada silver real
5. evoluir a API para serving analítico real
6. conectar Redshift ao consumo da API
