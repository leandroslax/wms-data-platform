# WMS Data Platform Architecture

## Objetivo
Descrever a arquitetura fim a fim do WMS Data Platform, do sistema fonte até a camada de consumo analítico.

## Visão geral
O projeto segue uma arquitetura orientada a lakehouse local e serving analítico:

1. Oracle WMS como sistema fonte
2. extração incremental e snapshots via cx_Oracle
3. persistência bruta em bronze (PostgreSQL)
4. normalização na silver (PostgreSQL)
5. transformação analítica com dbt-postgres
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
- extrair dados da origem via cx_Oracle
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
- PostgreSQL (schema `bronze`)

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
- dbt Core com dbt-postgres
- PostgreSQL como engine de transformação

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
- servir agentes analíticos

Estratégia:
- marts no schema `gold` do PostgreSQL
- dbt materializa os marts em tabelas consultáveis
- API e Grafana consomem diretamente do gold

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

Ferramentas:
- Grafana (local Docker, porta 3000) — dashboards de pipeline e negócio
- LangFuse — rastreamento de chamadas LLM
- DeepEval — avaliação de agentes
- logs de ingestão em arquivo e tabela de controle

## Princípios arquiteturais
- camadas bem definidas
- contratos explícitos entre estágios
- serving desacoplado da ingestão
- arquitetura local-first via Docker Compose
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
- `docs/postgres-query-contract.md`
