# PostgreSQL Query Contract

## Objetivo
Definir o contrato inicial de consulta ao PostgreSQL gold para a camada de serving analítico do WMS Data Platform.

## Papel do serving
O schema `gold` do PostgreSQL será a camada de serving analítico para consumo por:
- FastAPI
- Grafana
- agentes analíticos

## Princípios
- a API não consulta `bronze` diretamente
- a API não consulta `silver` diretamente
- a API consome marts estáveis e orientados a negócio
- o contrato da consulta deve ser explícito e versionável

## Escopo inicial do MVP
Endpoints cobertos:
- `/orders/summary`
- `/inventory/snapshot`
- `/movements/summary`

## Fonte esperada por endpoint

### Orders Summary
Tabela esperada:
- `gold.fct_orders`

Consulta lógica esperada:
- contagem de pedidos
- soma de unidades
- soma de receita

Resposta esperada:
- total_orders
- total_units
- total_revenue

### Inventory Snapshot
Tabela esperada:
- `gold.fct_inventory_snapshot`

Consulta lógica esperada:
- contagem de SKUs
- soma de estoque em mãos
- soma de estoque alocado
- soma de estoque disponível

Resposta esperada:
- total_skus
- total_on_hand_qty
- total_allocated_qty
- total_available_qty

### Movements Summary
Tabela esperada:
- `gold.fct_movements`

Consulta lógica esperada:
- contagem de movimentos
- soma de unidades movimentadas

Resposta esperada:
- total_movements
- total_units_moved

## Interface esperada na aplicação
A aplicação deve evoluir para um serviço de acesso a dados com métodos como:
- `fetch_orders_summary()`
- `fetch_inventory_snapshot()`
- `fetch_movements_summary()`

## Regras da camada de acesso
- encapsular SQL fora das rotas
- manter contrato estável de retorno
- permitir substituição de backend no futuro
- centralizar tratamento de erro de consulta
- registrar observabilidade de cada consulta

## Exemplo lógico de consulta

### Orders
```sql
select
    count(*) as total_orders,
    coalesce(sum(quantity), 0) as total_units,
    coalesce(sum(total_amount), 0) as total_revenue
from gold.fct_orders
```

### Inventory
```sql
select
    count(distinct product_id) as total_skus,
    coalesce(sum(on_hand_qty), 0) as total_on_hand_qty,
    coalesce(sum(allocated_qty), 0) as total_allocated_qty,
    coalesce(sum(available_qty), 0) as total_available_qty
from gold.fct_inventory_snapshot
```

### Movements
```sql
select
    count(*) as total_movements,
    coalesce(sum(quantity), 0) as total_units_moved
from gold.fct_movements
```

## Regras de segurança
- não expor credenciais na aplicação
- obter credenciais via variáveis de ambiente (.env)
- limitar permissões do usuário de consulta
- registrar falhas sem vazar detalhes sensíveis

## Regras de performance
- evitar consultas pesadas em tempo de request
- usar tabelas já agregadas quando necessário
- preferir serving preparado em vez de lógica complexa na API

## Próximos passos
1. evoluir `DataAccessService` para conexão real ao PostgreSQL gold
2. criar camada de configuração para conexão (host, porta, schema, usuário)
3. implementar consultas reais por endpoint
4. conectar observabilidade da API às consultas analíticas
