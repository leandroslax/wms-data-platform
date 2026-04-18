{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key='movement_id'
    )
}}

select
    movement_id,
    product_id,
    warehouse_id,
    depositor_id,
    qty_before,
    qty_after,
    qty_after - qty_before as qty_delta,
    movement_date,
    movement_status,
    operator_user,
    notes
from {{ ref('stg_movements') }}
