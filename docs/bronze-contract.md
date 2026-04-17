# Bronze Layer Contract

## Objetivo
Definir o contrato técnico da camada bronze do WMS Data Platform.

## Papel da camada bronze
A camada bronze representa a persistência bruta e auditável dos dados ingeridos do sistema fonte WMS.

Ela deve:
- preservar o payload original
- permitir rastreabilidade
- servir como ponto de reprocessamento
- desacoplar a origem da transformação analítica

## Princípios
- Não aplicar regra de negócio complexa na bronze.
- Não perder informação da origem.
- Preservar capacidade de auditoria e replay.
- Padronizar envelope de ingestão.
- Permitir evolução para Iceberg com governança.

## Formato de armazenamento
- storage: Amazon S3
- table format: Apache Iceberg
- catalog: AWS Glue Data Catalog
- granularidade inicial: por entidade
- particionamento inicial: por data de extração

## Entidades do MVP
- orders
- inventory
- movements

## Estrutura lógica esperada
Cada registro bronze deve conter:

- entity_name
- extraction_timestamp
- source_system
- source_table
- ingestion_run_id
- payload

## Definição dos campos de envelope

### entity_name
Nome lógico da entidade ingerida.
Exemplos:
- orders
- inventory
- movements

### extraction_timestamp
Timestamp UTC em que a extração foi executada.

### source_system
Identificador do sistema de origem.
Valor inicial esperado:
- oracle_wms

### source_table
Nome da tabela ou visão origem no sistema transacional.

### ingestion_run_id
Identificador único da execução de ingestão.

### payload
Objeto bruto contendo o registro original da origem.

## Localização esperada no data lake
Os dados bronze devem ser organizados no bucket:

- `s3://wms-dp-dev-bronze-us-east-1-896159010925/`

Estrutura lógica esperada:
- `orders/`
- `inventory/`
- `movements/`

## Estratégia inicial de particionamento
Particionar por data derivada de `extraction_timestamp`.

Exemplo lógico:
- `entity_name=orders/extraction_date=2026-04-17/`
- `entity_name=inventory/extraction_date=2026-04-17/`
- `entity_name=movements/extraction_date=2026-04-17/`

## Regras de escrita
- Cada execução deve registrar `ingestion_run_id`.
- O payload bruto não deve ser descartado.
- Campos derivados podem existir, mas não substituem o payload original.
- Reprocessamento deve ser possível sem dependência da camada silver.

## Regras de qualidade mínimas
- `entity_name` não pode ser nulo
- `extraction_timestamp` não pode ser nulo
- `source_system` não pode ser nulo
- `source_table` não pode ser nulo
- `ingestion_run_id` não pode ser nulo
- `payload` não pode ser nulo

## Relação com a camada silver
A camada silver será responsável por:
- tipagem
- deduplicação
- normalização
- padronização de nomes
- validação de qualidade

A bronze não é a camada final de consumo analítico.

## Relação com observabilidade
Cada carga bronze deve ser acompanhada por:
- volume lido
- volume gravado
- duração
- entidade
- status de execução
- checkpoint utilizado

## Próximos passos
1. alinhar os extratores Python ao envelope da bronze
2. definir a escrita física em Iceberg
3. padronizar checkpoints por entidade
4. conectar a bronze aos modelos staging do dbt
