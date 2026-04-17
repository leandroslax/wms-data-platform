# WMS Source System Contract

## Objetivo
Definir o contrato inicial entre o sistema fonte WMS e a plataforma de dados, antes da implementação definitiva de extração, modelos dbt e serving.

## Status
Este documento representa a camada de descoberta do projeto. Nenhuma tabela abaixo deve ser considerada definitiva até validação com a origem real.

## Entidades prioritárias

### 1. Orders
- Objetivo de negócio: acompanhar pedidos, status operacionais e volume expedido.
- Tabela ou visão origem: a definir
- Chave primária: a definir
- Colunas críticas esperadas:
  - order_id
  - customer_id
  - product_id
  - order_status
  - quantity
  - total_amount
  - created_at
  - updated_at
- Frequência esperada: incremental diária ou near real-time
- Sensibilidade: média
- Camada alvo:
  - bronze: ingestão bruta
  - silver: padronização e tipagem
  - gold: fatos de pedidos

### 2. Inventory
- Objetivo de negócio: acompanhar saldo, alocação e disponibilidade por produto/local.
- Tabela ou visão origem: a definir
- Chave primária: a definir
- Colunas críticas esperadas:
  - inventory_id
  - product_id
  - warehouse_id
  - location_id
  - on_hand_qty
  - allocated_qty
  - available_qty
  - snapshot_at
- Frequência esperada: snapshots periódicos
- Sensibilidade: média
- Camada alvo:
  - bronze: snapshot bruto
  - silver: normalização por localização
  - gold: fatos de estoque

### 3. Movements
- Objetivo de negócio: rastrear movimentações de estoque e eventos operacionais.
- Tabela ou visão origem: a definir
- Chave primária: a definir
- Colunas críticas esperadas:
  - movement_id
  - product_id
  - order_id
  - movement_type
  - quantity
  - source_location_id
  - target_location_id
  - moved_at
- Frequência esperada: incremental por evento
- Sensibilidade: média
- Camada alvo:
  - bronze: eventos brutos
  - silver: tipagem e deduplicação
  - gold: fatos de movimentação

### 4. Operators
- Objetivo de negócio: medir produtividade operacional por operador.
- Tabela ou visão origem: a definir
- Chave primária: a definir
- Colunas críticas esperadas:
  - operator_id
  - operator_name
  - shift
  - team
  - active_flag
- Frequência esperada: diária
- Sensibilidade: média
- Camada alvo:
  - bronze: cadastro bruto
  - silver: dimensão padronizada
  - gold: análises de produtividade

### 5. Tasks
- Objetivo de negócio: acompanhar execução de tarefas operacionais no armazém.
- Tabela ou visão origem: a definir
- Chave primária: a definir
- Colunas críticas esperadas:
  - task_id
  - operator_id
  - task_type
  - task_status
  - created_at
  - completed_at
- Frequência esperada: incremental por evento
- Sensibilidade: média
- Camada alvo:
  - bronze: tarefas brutas
  - silver: normalização
  - gold: fatos de execução operacional

### 6. Master Data
- Objetivo de negócio: fornecer dimensões de apoio para análise.
- Tabela ou visão origem: a definir
- Chave primária: a definir
- Colunas críticas esperadas:
  - product_id
  - sku
  - product_name
  - category
  - brand
- Frequência esperada: diária
- Sensibilidade: baixa
- Camada alvo:
  - bronze: cadastro bruto
  - silver: dimensão limpa
  - gold: dimensões analíticas

## Regras de validação antes da implementação
- Confirmar nome real da tabela ou visão na origem Oracle WMS.
- Confirmar chave primária ou estratégia de deduplicação.
- Confirmar coluna de atualização incremental.
- Confirmar política de mascaramento para campos sensíveis.
- Confirmar volumetria estimada por entidade.
- Confirmar destino em Iceberg, Glue Catalog e Redshift.

## Próximos passos
1. Validar as entidades prioritárias com a origem real.
2. Mapear tabelas e colunas reais.
3. Atualizar extratores Python com base nesse contrato.
4. Atualizar dbt staging com os nomes reais.
5. Construir marts e serving apenas após validação da camada silver.
