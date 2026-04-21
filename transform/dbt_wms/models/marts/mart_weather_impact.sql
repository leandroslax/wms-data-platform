{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['company_id', 'depositor_id', 'issued_date']
    )
}}

-- Delay metrics correlated with weather data by company, depositor and day.
-- Weather sourced from bronze.weather_daily (Open-Meteo), populated by dag_enrich_geo.
-- JOIN logic: order's company → geo_reference → UF → weather_daily (same date).
-- Enables Grafana panels correlating delay_rate_pct with precipitation / temperature.

with order_delays as (
    select
        company_id,
        depositor_id,
        cast(date_trunc('day', issued_at) as date)   as issued_date,
        date_trunc('month', issued_at)               as issued_month,
        count(*)                                      as order_count,
        avg(
            case
                when delivered_at is not null and issued_at is not null
                then ({{ wms_epoch("delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0
            end
        )                                             as avg_cycle_time_hours,
        count(case
            when delivered_at is not null
             and ({{ wms_epoch("delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0 > 48
            then 1
        end)                                          as delayed_order_count,
        {{ wms_round(
            "count(case when delivered_at is not null and (" ~
            wms_epoch("delivered_at") ~ " - " ~ wms_epoch("issued_at") ~
            ") / 3600.0 > 48 then 1 end) * 100.0 / nullif(count(*), 0)",
            2
        ) }}                                          as delay_rate_pct
    from {{ ref('fct_orders') }}
    where issued_at is not null
    group by 1, 2, 3, 4
),

-- Resolve company → UF via geo_reference
company_uf as (
    select
        entity_id as company_id,
        uf
    from {{ source('bronze', 'geo_reference') }}
    where entity_type = 'company'
),

-- Bring in weather for the order date × company UF
order_weather as (
    select
        od.company_id,
        od.depositor_id,
        od.issued_date,
        od.issued_month,
        od.order_count,
        od.avg_cycle_time_hours,
        od.delayed_order_count,
        od.delay_rate_pct,
        wd.weather_condition,
        wd.avg_temperature_c,
        wd.precipitation_mm,
        wd.wind_speed_kmh
    from order_delays od
    left join company_uf cu
        on cu.company_id = od.company_id
    left join {{ source('bronze', 'weather_daily') }} wd
        on  wd.location_uf  = cu.uf
        and wd.weather_date = od.issued_date
)

select * from order_weather

{% if is_incremental() %}
where issued_date > (select max(issued_date) from {{ this }})
{% endif %}
