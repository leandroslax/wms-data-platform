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
        min_stock_qty        as current_stock,
        safety_stock_qty,
        reorder_point,
        avg_consumption      as avg_daily_consumption,
        case
            when avg_consumption > 0
            then round(min_stock_qty / avg_consumption, 1)
            else null
        end as days_to_stockout
    from {{ ref('fct_inventory_snapshot') }}
),

classified as (
    select
        *,
        case
            when days_to_stockout is null   then 'unknown'
            when days_to_stockout <= 0      then 'stockout'
            when days_to_stockout <= 3      then 'critical'
            when days_to_stockout <= 7      then 'high'
            when days_to_stockout <= 14     then 'medium'
            else                                 'low'
        end as risk_level,
        current_date() as snapshot_date
    from base
)

select * from classified
