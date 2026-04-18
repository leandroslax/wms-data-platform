{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['warehouse_id', 'company_id', 'product_class']
    )
}}

-- Inventory health aggregated by warehouse and product class.
-- Geographic enrichment (warehouse CEP → city/state) is not yet implemented.
-- Once ViaCEP pipeline is active, join on warehouse master data to add
-- city, state and lat/long columns for choropleth maps in Grafana.

select
    warehouse_id,
    company_id,
    product_class,
    count(distinct product_id)                                              as product_count,
    sum(min_stock_qty)                                                      as total_current_stock,
    sum(safety_stock_qty)                                                   as total_safety_stock,
    sum(ideal_stock_qty)                                                    as total_ideal_stock,
    round(
        avg(case when avg_consumption > 0
            then min_stock_qty / avg_consumption end),
        1
    )                                                                       as avg_coverage_days,
    count(case when min_stock_qty <= safety_stock_qty then 1 end)           as stockout_count,
    count(case when min_stock_qty <= reorder_point    then 1 end)           as below_reorder_count,
    round(
        count(case when min_stock_qty > safety_stock_qty then 1 end)
        * 100.0 / nullif(count(*), 0),
        2
    )                                                                       as stock_health_pct
from {{ ref('fct_inventory_snapshot') }}
group by 1, 2, 3
