{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key='order_id'
    )
}}

with base as (
    select
        order_id,
        document_number,
        document_type,
        company_id,
        depositor_id,
        issued_at,
        delivered_at,
        total_value,
        case
            when delivered_at is not null and issued_at is not null
            then ({{ wms_epoch("delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0
            else null
        end as cycle_time_hours
    from {{ ref('fct_orders') }}
    where issued_at is not null
),

classified as (
    select
        *,
        48                                    as sla_target_hours,
        date_trunc('day', issued_at)          as issued_date,
        date_trunc('month', issued_at)        as issued_month,
        case
            when cycle_time_hours is null     then 'pending'
            when cycle_time_hours <= 24       then 'on_time_express'
            when cycle_time_hours <= 48       then 'on_time'
            when cycle_time_hours <= 72       then 'at_risk'
            else                                   'late'
        end as sla_status
    from base
)

select * from classified

{% if is_incremental() %}
where issued_at > (select max(issued_at) from {{ this }})
{% endif %}
