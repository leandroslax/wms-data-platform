{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key='product_id'
    )
}}

with ranked as (
    select
        product_id,
        company_id,
        warehouse_id,
        product_class,
        row_number() over (
            partition by product_id
            order by warehouse_id, company_id
        ) as _rn
    from {{ ref('stg_inventory') }}
    where product_id is not null
)

select
    product_id,
    company_id,
    warehouse_id,
    product_class
from ranked
where _rn = 1
