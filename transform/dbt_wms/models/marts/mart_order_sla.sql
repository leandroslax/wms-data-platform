{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key='order_id'
    )
}}

-- Deriva "delivered_at" via primeiro movimento de saída (estadomovimento=8)
-- do mesmo depositante após a emissão do documento.
-- DATAENTREGA não é preenchida nesta instalação do Oracle WMS.
with first_output_movement as (
    select
        cast(codigodepositante as {{ dbt.type_string() }}) as depositor_id,
        cast(datamovimento     as {{ dbt.type_timestamp() }}) as movement_at
    from {{ source('bronze', 'movements_entrada_saida') }}
    where cast(estadomovimento as text) = '8'
),

base as (
    select
        o.order_id,
        o.document_number,
        o.document_type,
        o.company_id,
        o.depositor_id,
        o.issued_at,
        o.delivered_at,
        o.total_value,
        -- proxy de entrega: menor movimento de saída do depositante após emissão
        min(m.movement_at) as delivered_at_proxy
    from {{ ref('fct_orders') }} o
    left join first_output_movement m
        on  m.depositor_id = o.depositor_id
        and m.movement_at  > o.issued_at
    where o.issued_at is not null
    group by
        o.order_id, o.document_number, o.document_type,
        o.company_id, o.depositor_id, o.issued_at,
        o.delivered_at, o.total_value
),

enriched as (
    select
        *,
        coalesce(delivered_at, delivered_at_proxy) as resolved_delivered_at
    from base
),

classified as (
    select
        order_id,
        document_number,
        document_type,
        company_id,
        depositor_id,
        issued_at,
        delivered_at,
        delivered_at_proxy,
        resolved_delivered_at,
        total_value,
        48 as sla_target_hours,
        date_trunc('day',   issued_at) as issued_date,
        date_trunc('month', issued_at) as issued_month,
        case
            when resolved_delivered_at is not null
            then ({{ wms_epoch("resolved_delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0
            else null
        end as cycle_time_hours,
        case
            when resolved_delivered_at is null then 'pending'
            when ({{ wms_epoch("resolved_delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0 <= 24  then 'on_time_express'
            when ({{ wms_epoch("resolved_delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0 <= 48  then 'on_time'
            when ({{ wms_epoch("resolved_delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0 <= 72  then 'at_risk'
            else 'late'
        end as sla_status,
        case
            when resolved_delivered_at is not null then true
            else false
        end as sla_met
    from enriched
)

select * from classified

{% if is_incremental() %}
where issued_at > (select max(issued_at) from {{ this }})
{% endif %}
