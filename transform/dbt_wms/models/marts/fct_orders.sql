{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key='order_id'
    )
}}

select
    order_id,
    document_number,
    document_series,
    document_type,
    company_id,
    depositor_id,
    issued_at,
    delivered_at,
    total_value,
    integration_seq
from {{ ref('stg_orders') }}
