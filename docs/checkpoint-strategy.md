# Checkpoint Strategy

## Objetivo
Definir a estratégia de checkpoint dos extratores do WMS Data Platform para suportar cargas incrementais, reprocessamento controlado e rastreabilidade operacional.

## Papel do checkpoint
O checkpoint registra o último ponto válido de ingestão de cada entidade.

Ele serve para:
- evitar reprocessamento desnecessário
- permitir cargas incrementais
- suportar retomada após falha
- fornecer rastreabilidade da execução

## Escopo inicial
A estratégia cobre as entidades do MVP:
- orders
- inventory
- movements

## Local de armazenamento
Os checkpoints devem ser armazenados no bucket de artifacts:

- `s3://wms-dp-dev-artifacts-us-east-1-896159010925/`

Estrutura lógica inicial:
- `checkpoints/orders.json`
- `checkpoints/inventory.json`
- `checkpoints/movements.json`

## Estrutura lógica esperada do checkpoint
Cada entidade deve ter um documento com os seguintes campos:

- entity_name
- source_system
- checkpoint_type
- last_successful_value
- last_successful_run_id
- last_successful_timestamp
- extraction_window_start
- extraction_window_end
- status

## Definição dos campos

### entity_name
Nome lógico da entidade.
Exemplos:
- orders
- inventory
- movements

### source_system
Sistema de origem.
Valor inicial esperado:
- oracle_wms

### checkpoint_type
Tipo de controle incremental utilizado.
Valores esperados:
- timestamp
- id
- snapshot

### last_successful_value
Último valor incremental válido processado com sucesso.
Exemplos:
- timestamp máximo
- id máximo
- data de snapshot

### last_successful_run_id
Identificador da execução que consolidou esse checkpoint.

### last_successful_timestamp
Timestamp UTC da última execução bem-sucedida.

### extraction_window_start
Início da janela usada na última execução.

### extraction_window_end
Fim da janela usada na última execução.

### status
Estado do checkpoint.
Valores esperados:
- success
- failed
- partial

## Estratégia por entidade

### Orders
Tipo inicial:
- `timestamp`

Campo incremental preferencial:
- `updated_at`

Fallback:
- carga completa controlada quando a origem não suportar incrementalidade segura

### Inventory
Tipo inicial:
- `snapshot`

Campo incremental preferencial:
- `snapshot_at`

Estratégia:
- cada execução representa uma fotografia do estado do estoque

### Movements
Tipo inicial:
- `timestamp`

Campo incremental preferencial:
- `moved_at`

Fallback:
- combinação com id técnico quando necessário

## Regra de atualização do checkpoint
O checkpoint só deve ser atualizado quando:
- a extração terminar com sucesso
- a persistência bronze terminar com sucesso
- o volume mínimo esperado não indicar falha silenciosa

## Regra de falha
Se a execução falhar:
- não sobrescrever o último checkpoint válido
- registrar status de falha em log
- permitir nova execução com base no último ponto consistente

## Reprocessamento
A estratégia deve permitir:
- replay completo por entidade
- replay por janela temporal
- reset controlado do checkpoint
- bootstrap inicial sem histórico

## Observabilidade
Cada uso de checkpoint deve registrar:
- entidade
- valor anterior
- valor novo
- run_id
- janela processada
- status final

## Exemplo lógico de checkpoint
```json
{
  "entity_name": "orders",
  "source_system": "oracle_wms",
  "checkpoint_type": "timestamp",
  "last_successful_value": "2026-04-17T13:00:00Z",
  "last_successful_run_id": "orders-2026-04-17T13-05-00Z",
  "last_successful_timestamp": "2026-04-17T13:06:10Z",
  "extraction_window_start": "2026-04-17T12:00:00Z",
  "extraction_window_end": "2026-04-17T13:00:00Z",
  "status": "success"
}

