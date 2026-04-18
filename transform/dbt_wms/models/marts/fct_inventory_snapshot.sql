{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key='inventory_id'
    )
}}

select
    inventory_id,
    product_id,
    warehouse_id,
    company_id,
    ideal_stock_qty,
    min_stock_qty,
    max_stock_qty,
    safety_stock_qty,
    reorder_point,
    avg_consumption,
    product_class
from {{ ref('stg_inventory') }}
