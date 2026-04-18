{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key='inventory_id'
    )
}}

with base as (
    select
        inventory_id,
        product_id,
        warehouse_id,
        company_id,
        product_class,
        min_stock_qty,
        max_stock_qty,
        ideal_stock_qty,
        safety_stock_qty,
        reorder_point,
        avg_consumption
    from {{ ref('fct_inventory_snapshot') }}
),

enriched as (
    select
        *,
        case
            when avg_consumption > 0
            then {{ wms_round("min_stock_qty / avg_consumption", 1) }}
            else null
        end as coverage_days,

        case
            when ideal_stock_qty > 0
            then {{ wms_round("min_stock_qty / ideal_stock_qty", 2) }}
            else null
        end as stock_utilization_rate,

        case
            when avg_consumption > 0 and min_stock_qty / avg_consumption <= 3  then 'critical'
            when avg_consumption > 0 and min_stock_qty / avg_consumption <= 7  then 'high'
            when avg_consumption > 0 and min_stock_qty / avg_consumption <= 14 then 'medium'
            when avg_consumption > 0                                            then 'healthy'
            else 'unknown'
        end as stockout_risk,

        case when min_stock_qty <= safety_stock_qty then true else false end as below_safety_stock,
        case when min_stock_qty <= reorder_point    then true else false end as below_reorder_point
    from base
)

select * from enriched
