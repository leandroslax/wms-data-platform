# Serving Strategy

## Objetivo
Definir a estratégia de serving analítico do WMS Data Platform para suportar API, dashboards e futura camada de agentes.

## Papel da camada de serving
A camada de serving representa o ponto de consumo dos dados transformados para aplicações analíticas e operacionais.

Ela deve:
- expor dados consistentes para a API
- suportar consultas rápidas para dashboards
- servir como base para agentes analíticos futuros
- desacoplar a camada de transformação do consumo final

## Princípios
- serving consome dados já modelados
- serving não substitui transformação
- serving deve ser orientado a casos de uso
- serving deve privilegiar estabilidade semântica

## Estratégia do projeto
A estratégia do projeto será dividida em duas etapas:

### Etapa 1. MVP
- API servindo respostas a partir de uma camada de acesso a dados mockada ou simplificada
- contrato de endpoints definido
- modelo de consumo preparado para integração futura

### Etapa 2. Produção analítica
- dados consumidos a partir de marts derivados da silver
- serving conectado ao Redshift
- API consultando tabelas estáveis e orientadas a consumo

## Fonte analítica esperada
Marts do MVP:
- `fct_orders`
- `fct_inventory_snapshot`
- `fct_movements`

Dimensões iniciais:
- `dim_products`

## Consumidores da camada de serving
- FastAPI
- dashboards operacionais
- dashboards executivos
- agentes analíticos
- futuras consultas de copiloto

## Contrato por endpoint do MVP

### `/orders/summary`
Fonte esperada:
- `fct_orders`

Métricas esperadas:
- total_orders
- total_units
- total_revenue

### `/inventory/snapshot`
Fonte esperada:
- `fct_inventory_snapshot`

Métricas esperadas:
- total_skus
- total_on_hand_qty
- total_allocated_qty
- total_available_qty

### `/movements/summary`
Fonte esperada:
- `fct_movements`

Métricas esperadas:
- total_movements
- total_units_moved

## Arquitetura alvo de serving
Fluxo esperado:

1. extratores alimentam bronze
2. bronze gera silver normalizada
3. dbt produz marts analíticos
4. marts são disponibilizados para serving
5. API consulta serving
6. dashboards e agentes reutilizam os mesmos contratos

## Estratégia tecnológica
- armazenamento lakehouse: S3 + Iceberg
- catálogo: Glue Data Catalog
- transformação: dbt + Glue
- serving analítico: Redshift
- API: FastAPI

## Regras de modelagem para serving
- tabelas de serving devem ser orientadas a consulta
- evitar lógica complexa em tempo de request
- preferir métricas pré-modeladas quando fizer sentido
- manter consistência entre API e dashboards

## Observabilidade
A camada de serving deve futuramente registrar:
- latência de consulta
- volume retornado
- erros por endpoint
- custo de consulta quando aplicável

## Próximos passos
1. ligar `DataAccessService` a uma fonte analítica real
2. definir contrato de consulta ao Redshift
3. alinhar marts do dbt às necessidades da API
4. conectar serving aos agentes analíticos do projeto
