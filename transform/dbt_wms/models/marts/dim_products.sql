{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['product_id', 'warehouse_id']
    )
}}

-- Product dimension keyed by product + warehouse.
-- One row per (product_id, warehouse_id) combination so that
-- downstream joins can resolve class and company per storage location.
-- The previous ROW_NUMBER dedup (unique_key='product_id') collapsed
-- all warehouses to a single row and silently dropped warehouse data.

select distinct
    product_id,
    warehouse_id,
    company_id,
    product_class
from {{ ref('stg_inventory') }}
where product_id is not null
