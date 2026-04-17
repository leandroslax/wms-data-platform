# WMS Entity to Extractor Mapping

## Objetivo
Relacionar cada entidade priorizada do WMS ao extractor responsável, à camada bronze e ao destino analítico esperado.

## Princípio
Este documento ainda representa uma proposta inicial. O mapeamento definitivo depende da confirmação das tabelas reais do Oracle WMS.

| Entidade     | Arquivo extractor                              | Origem real | Bronze target | Silver target      | Gold target                | Status |
|--------------|--------------------------------------------------|-------------|---------------|--------------------|----------------------------|--------|
| Orders       | pipelines/extraction/extractors/orders.py        | A definir   | bronze.orders | stg_orders         | fct_orders                 | Draft  |
| Inventory    | pipelines/extraction/extractors/inventory.py     | A definir   | bronze.inventory | stg_inventory    | fct_inventory_snapshot     | Draft  |
| Movements    | pipelines/extraction/extractors/movements.py     | A definir   | bronze.movements | stg_movements    | fct_movements              | Draft  |
| Operators    | pipelines/extraction/extractors/operators.py     | A definir   | bronze.operators | dim_operators    | mart_operator_productivity | Draft  |
| Tasks        | pipelines/extraction/extractors/tasks.py         | A definir   | bronze.tasks  | stg_tasks          | fct_tasks                  | Draft  |
| Master Data  | pipelines/extraction/extractors/master_data.py   | A definir   | bronze.master_data | dim_products   | dim_products               | Draft  |

## Regras de implementação
- Cada extractor deve ter um contrato explícito de entrada e saída.
- Cada entidade deve ter uma estratégia de incrementalidade definida.
- Cada carga bronze deve preservar o payload bruto necessário para auditoria.
- Silver deve aplicar padronização, tipagem e deduplicação.
- Gold deve ser orientado a consumo analítico e API.

## Próximos passos
1. Confirmar quais 3 entidades entram primeiro no MVP.
2. Validar nomes reais das tabelas Oracle WMS.
3. Atualizar cada extractor com o source contract definitivo.
4. Ajustar modelos dbt após validação da camada bronze.
