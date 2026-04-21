{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['product_id', 'warehouse_id', 'company_id', 'product_class']
    )
}}

-- Product dimension keyed by product + warehouse + company + class.
-- The inventory snapshot contains the same product/warehouse repeated
-- across multiple companies, so merge needs the business grain below.

select distinct
    product_id,
    warehouse_id,
    company_id,
    product_class
from {{ ref('stg_inventory') }}
where product_id is not null
  and warehouse_id is not null
  and company_id is not null
  and product_class is not null
