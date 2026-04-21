{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['warehouse_id', 'company_id', 'product_class']
    )
}}

-- Inventory health aggregated by warehouse and product class with geographic enrichment.
-- Warehouse location (city/state/region/lat-long) sourced from bronze.geo_reference,
-- populated by the ViaCEP enrichment pipeline (dag_enrich_geo).
-- Used for choropleth maps in Grafana (mart_geo_inventory dashboard).

with inventory_agg as (
    select
        warehouse_id,
        company_id,
        product_class,
        count(distinct product_id)                                              as product_count,
        sum(min_stock_qty)                                                      as total_current_stock,
        sum(safety_stock_qty)                                                   as total_safety_stock,
        sum(ideal_stock_qty)                                                    as total_ideal_stock,
        {{ wms_round(
            "avg(case when avg_consumption > 0 then min_stock_qty / avg_consumption end)",
            1
        ) }}                                                                    as avg_coverage_days,
        count(case when min_stock_qty <= safety_stock_qty then 1 end)           as stockout_count,
        count(case when min_stock_qty <= reorder_point    then 1 end)           as below_reorder_count,
        {{ wms_round(
            "count(case when min_stock_qty > safety_stock_qty then 1 end) * 100.0 / nullif(count(*), 0)",
            2
        ) }}                                                                    as stock_health_pct
    from {{ ref('fct_inventory_snapshot') }}
    group by 1, 2, 3
),

warehouse_geo as (
    select
        entity_id       as warehouse_id,
        localidade      as cidade,
        uf,
        estado,
        regiao,
        latitude,
        longitude
    from {{ source('bronze', 'geo_reference') }}
    where entity_type = 'warehouse'
)

select
    i.warehouse_id,
    i.company_id,
    i.product_class,
    i.product_count,
    i.total_current_stock,
    i.total_safety_stock,
    i.total_ideal_stock,
    i.avg_coverage_days,
    i.stockout_count,
    i.below_reorder_count,
    i.stock_health_pct,
    -- Geographic dimensions from warehouse geo_reference
    g.cidade,
    g.uf,
    g.estado,
    g.regiao,
    g.latitude,
    g.longitude
from inventory_agg i
left join warehouse_geo g on g.warehouse_id = i.warehouse_id
