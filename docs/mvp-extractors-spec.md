# MVP Extractors Specification

## Objetivo
Definir o comportamento esperado dos 3 extratores do MVP da plataforma WMS.

## Escopo
Este documento cobre:
- orders
- inventory
- movements

## Padrão comum dos extratores
Todos os extratores do MVP devem seguir estas regras:

- Ler dados da origem Oracle WMS ou fonte mock equivalente.
- Produzir payload bruto para a camada bronze.
- Preservar campos necessários para auditoria.
- Registrar metadados de execução.
- Ser compatíveis com execução local e futura execução em Lambda.
- Permitir incrementalidade quando aplicável.

## Estrutura esperada de saída bronze
Cada extractor deve gravar registros com este envelope lógico:

- entity_name
- extraction_timestamp
- source_system
- source_table
- payload

## 1. Orders Extractor

### Arquivo
`pipelines/extraction/extractors/orders.py`

### Objetivo
Extrair pedidos e eventos de pedido do WMS.

### Responsabilidades
- Ler pedidos da origem.
- Identificar status operacionais.
- Preservar timestamps de criação e atualização.
- Entregar dados prontos para bronze.

### Campos esperados
- order_id
- customer_id
- product_id
- order_status
- payment_status
- quantity
- total_amount
- created_at
- updated_at

### Estratégia inicial
- carga incremental por `updated_at`, quando existir
- fallback para carga completa controlada em ambiente local

## 2. Inventory Extractor

### Arquivo
`pipelines/extraction/extractors/inventory.py`

### Objetivo
Extrair snapshots de posição de estoque.

### Responsabilidades
- Ler saldo em mãos, alocado e disponível.
- Preservar referência de warehouse e localização.
- Produzir registros orientados a snapshot.

### Campos esperados
- inventory_id
- product_id
- warehouse_id
- location_id
- on_hand_qty
- allocated_qty
- available_qty
- snapshot_at

### Estratégia inicial
- snapshot por janela de execução
- persistência integral de cada fotografia

## 3. Movements Extractor

### Arquivo
`pipelines/extraction/extractors/movements.py`

### Objetivo
Extrair eventos de movimentação de estoque.

### Responsabilidades
- Ler eventos de entrada, saída e transferência.
- Preservar referência de origem e destino.
- Registrar timestamp do movimento.

### Campos esperados
- movement_id
- product_id
- order_id
- movement_type
- quantity
- source_location_id
- target_location_id
- moved_at

### Estratégia inicial
- carga incremental por evento ou timestamp de movimento
- deduplicação posterior na camada silver

## Regras de observabilidade
Cada extractor deve produzir logs com:
- nome da entidade
- quantidade de registros lidos
- quantidade de registros gravados
- duração da execução
- checkpoint utilizado

## Regras de qualidade
- falhar explicitamente em caso de schema inesperado
- registrar warnings para campos nulos críticos
- não mascarar erro estrutural da origem

## Próximos passos
1. alinhar os arquivos Python de extractor com esta especificação
2. definir contrato de checkpoint por entidade
3. definir estratégia de escrita Iceberg/bronze
4. conectar esses extratores à orquestração futura
