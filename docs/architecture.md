# WMS Data Platform Architecture

## Objetivo
Descrever a arquitetura fim a fim do WMS Data Platform, do sistema fonte até a camada de consumo analítico.

## Visão geral
O projeto segue uma arquitetura orientada a lakehouse e serving analítico:

1. Oracle WMS como sistema fonte
2. extração incremental e snapshots
3. persistência bruta em bronze
4. normalização na silver
5. transformação analítica com dbt
6. serving para API, dashboards e agentes

## Camadas da arquitetura

### 1. Source System
Sistema transacional de origem:
- Oracle WMS

Entidades prioritárias do MVP:
- orders
- inventory
- movements

## 2. Ingestion
Responsável por:
- extrair dados da origem
- registrar checkpoints
- produzir envelopes de ingestão
- persistir dados na bronze

Componentes principais:
- `pipelines/extraction/oracle_connector.py`
- `pipelines/extraction/checkpoint.py`
- `pipelines/extraction/extractors/orders.py`
- `pipelines/extraction/extractors/inventory.py`
- `pipelines/extraction/extractors/movements.py`

## 3. Bronze
Responsável por:
- preservar payload bruto
- manter rastreabilidade
- suportar replay e auditoria

Tecnologia:
- S3
- Apache Iceberg
- Glue Data Catalog

Bucket bronze:
- `s3://wms-dp-dev-bronze-us-east-1-896159010925/`

## 4. Silver
Responsável por:
- tipagem
- padronização
- deduplicação
- preparação semântica para transformação

Entidades silver do MVP:
- `silver.orders`
- `silver.inventory`
- `silver.movements`

## 5. Transformation
Responsável por:
- staging analítico
- facts e dimensions
- preparação para consumo

Tecnologia:
- dbt
- Glue para transformação
- Redshift como serving analítico futuro

Modelos iniciais:
- `stg_orders`
- `stg_inventory`
- `stg_movements`
- `fct_orders`
- `fct_inventory_snapshot`
- `fct_movements`
- `dim_products`

## 6. Serving
Responsável por:
- disponibilizar métricas e dados de consumo
- atender API
- alimentar dashboards
- servir agentes analíticos no futuro

Estratégia:
- MVP com camada mockada de acesso
- evolução posterior para Redshift

## 7. API
Responsável por:
- expor contratos HTTP estáveis
- fornecer endpoints do MVP
- desacoplar consumidores da infraestrutura analítica

Endpoints do MVP:
- `/health`
- `/metadata`
- `/orders/summary`
- `/inventory/snapshot`
- `/movements/summary`

## 8. Observabilidade
Responsável por:
- monitorar execução
- acompanhar falhas
- registrar comportamento analítico
- suportar operação e troubleshooting

Ferramentas previstas:
- CloudWatch
- SNS
- LangFuse
- DeepEval
- logs de ingestão
- métricas de query

## Princípios arquiteturais
- camadas bem definidas
- contratos explícitos entre estágios
- serving desacoplado da ingestão
- infraestrutura como código
- rastreabilidade ponta a ponta
- desenho evolutivo orientado a MVP

## Escopo atual do MVP
O MVP está focado em:
- orders
- inventory
- movements

Essas entidades sustentam:
- pipeline inicial
- transformação dbt
- API analítica
- dashboards operacionais
- futura camada de agentes

## Documentos relacionados
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
