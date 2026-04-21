{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['company_id', 'depositor_id', 'issued_month']
    )
}}

{% set has_geo_reference = wms_source_exists('bronze', 'geo_reference') %}

-- SLA performance aggregated by company and depositor with geographic enrichment.
-- Geography (city/state/region/lat-long) sourced from bronze.geo_reference,
-- populated by the ViaCEP enrichment pipeline (dag_enrich_geo).

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
),

-- Geographic enrichment: company entity_id maps to depositor/company codes
company_geo as (
    {% if has_geo_reference %}
    select
        entity_id,
        localidade  as cidade,
        uf,
        estado,
        regiao,
        latitude,
        longitude
    from {{ source('bronze', 'geo_reference') }}
    where entity_type = 'company'
    {% else %}
    select
        cast(null as text)    as entity_id,
        cast(null as text)    as cidade,
        cast(null as text)    as uf,
        cast(null as text)    as estado,
        cast(null as text)    as regiao,
        cast(null as numeric) as latitude,
        cast(null as numeric) as longitude
    where 1 = 0
    {% endif %}
),

-- Fallback: warehouse geo when company geo is unavailable
depositor_geo as (
    {% if has_geo_reference %}
    select
        entity_id,
        localidade  as cidade,
        uf,
        estado,
        regiao,
        latitude,
        longitude
    from {{ source('bronze', 'geo_reference') }}
    where entity_type = 'warehouse'
    {% else %}
    select
        cast(null as text)    as entity_id,
        cast(null as text)    as cidade,
        cast(null as text)    as uf,
        cast(null as text)    as estado,
        cast(null as text)    as regiao,
        cast(null as numeric) as latitude,
        cast(null as numeric) as longitude
    where 1 = 0
    {% endif %}
)

select
    s.company_id,
    s.depositor_id,
    s.issued_month,
    s.order_count,
    s.delivered_count,
    s.total_value,
    s.avg_cycle_time_hours,
    s.sla_compliance_pct,
    s.late_delivery_pct,
    -- Geographic dimensions (company geo takes precedence over warehouse geo)
    coalesce(cg.cidade,   dg.cidade)   as cidade,
    coalesce(cg.uf,       dg.uf)       as uf,
    coalesce(cg.estado,   dg.estado)   as estado,
    coalesce(cg.regiao,   dg.regiao)   as regiao,
    coalesce(cg.latitude, dg.latitude) as latitude,
    coalesce(cg.longitude,dg.longitude)as longitude
from sla_base s
left join company_geo  cg on cg.entity_id = s.company_id
left join depositor_geo dg on dg.entity_id = s.depositor_id

{% if is_incremental() %}
where s.issued_month > (select max(issued_month) from {{ this }})
{% endif %}
