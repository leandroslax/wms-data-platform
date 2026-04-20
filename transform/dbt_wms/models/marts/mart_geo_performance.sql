{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['company_id', 'depositor_id', 'issued_month']
    )
}}

-- SLA performance aggregated by company and depositor.
-- Geographic enrichment (CEP → city/state via ViaCEP) is not yet implemented.
-- Once the enrichment pipeline is active, add city/state/region columns via JOIN
-- on the enriched bronze tables.

with sla_base as (
    select
        company_id,
        depositor_id,
        date_trunc('month', issued_at) as issued_month,
        count(*)                        as order_count,
        count(case when delivered_at is not null then 1 end)
                                        as delivered_count,
        sum(total_value)                as total_value,
        avg(
            case
                when delivered_at is not null and issued_at is not null
                then ({{ wms_epoch("delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0
            end
        )                               as avg_cycle_time_hours,
        round(
            count(case
                when delivered_at is not null
                 and ({{ wms_epoch("delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0 <= 48
                then 1
            end) * 100.0 / nullif(count(*), 0),
            2
        )                               as sla_compliance_pct,
        round(
            count(case
                when delivered_at is not null
                 and ({{ wms_epoch("delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0 > 48
                then 1
            end) * 100.0 / nullif(count(*), 0),
            2
        )                               as late_delivery_pct
    from {{ ref('fct_orders') }}
    where issued_at is not null
    group by 1, 2, 3
)

select * from sla_base

{% if is_incremental() %}
where issued_month > (select max(issued_month) from {{ this }})
{% endif %}
