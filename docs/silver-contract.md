# Silver Layer Contract

## Objetivo
Definir o contrato técnico da camada silver do WMS Data Platform.

## Papel da camada silver
A camada silver representa a normalização dos dados ingeridos na bronze.

Ela deve:
- aplicar tipagem
- padronizar nomes de campos
- remover duplicidades quando necessário
- separar payload bruto de estrutura analítica
- preparar os dados para consumo por dbt marts, API e serving analítico

## Princípios
- silver não é camada final de negócio
- silver deve ser reprodutível a partir da bronze
- silver deve ser semanticamente estável
- silver deve reduzir ambiguidade estrutural sem perder rastreabilidade

## Fonte da silver
A camada silver é derivada exclusivamente da bronze.

Entidades do MVP:
- orders
- inventory
- movements

## Responsabilidades da silver
- extrair campos do envelope bronze
- tipar colunas
- padronizar nomenclatura
- registrar colunas técnicas de lineage
- deduplicar quando aplicável
- preservar referência ao `ingestion_run_id`

## Envelope de entrada esperado da bronze
Campos mínimos:
- entity_name
- extraction_timestamp
- source_system
- source_table
- ingestion_run_id
- payload

## Estrutura lógica esperada por entidade

### Orders
Tabela lógica esperada:
- `silver.orders`

Colunas mínimas esperadas:
- order_id
- customer_id
- product_id
- order_status
- payment_status
- quantity
- total_amount
- created_at
- updated_at
- ingestion_run_id
- extraction_timestamp

### Inventory
Tabela lógica esperada:
- `silver.inventory`

Colunas mínimas esperadas:
- inventory_id
- product_id
- warehouse_id
- location_id
- on_hand_qty
- allocated_qty
- available_qty
- snapshot_at
- ingestion_run_id
- extraction_timestamp

### Movements
Tabela lógica esperada:
- `silver.movements`

Colunas mínimas esperadas:
- movement_id
- product_id
- order_id
- movement_type
- quantity
- source_location_id
- target_location_id
- moved_at
- ingestion_run_id
- extraction_timestamp

## Regras de padronização
- nomes de colunas em snake_case
- ids como string quando houver ambiguidade na origem
- datas e timestamps tipados explicitamente
- quantidades como integer
- valores monetários como numeric/double conforme engine

## Regras de deduplicação
- orders: por `order_id`, priorizando o maior `updated_at`
- inventory: por `inventory_id` ou chave composta validada com origem
- movements: por `movement_id`, priorizando evento mais recente

## Colunas técnicas obrigatórias
Toda tabela silver deve conter:
- ingestion_run_id
- extraction_timestamp
- source_system
- source_table

## Regras de qualidade mínimas
- chave primária lógica não nula
- timestamps críticos não nulos quando exigidos
- tipos coerentes com a definição da entidade
- rejeição explícita de schema incompatível

## Relação com dbt staging
Os modelos `stg_*` devem refletir a silver já tipada e padronizada.

Mapeamento esperado:
- `stg_orders` <- `silver.orders`
- `stg_inventory` <- `silver.inventory`
- `stg_movements` <- `silver.movements`

## Relação com marts
Os marts devem consumir exclusivamente a silver ou staging derivado dela.

Exemplos do MVP:
- `fct_orders`
- `fct_inventory_snapshot`
- `fct_movements`

## Observabilidade
Cada transformação silver deve registrar:
- entidade processada
- volume de entrada
- volume de saída
- quantidade deduplicada
- duração
- run_id associado

## Próximos passos
1. alinhar dbt staging ao contrato silver
2. revisar extratores para garantir envelope bronze completo
3. preparar marts do MVP consumindo a silver
4. conectar API ao serving derivado dos marts
