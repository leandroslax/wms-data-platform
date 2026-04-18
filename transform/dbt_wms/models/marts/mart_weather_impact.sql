{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['company_id', 'depositor_id', 'issued_date']
    )
}}

-- Delay metrics by company, depositor and day.
-- INMET weather data is not yet integrated — weather_condition column is a
-- placeholder until the enrichment pipeline (Lambda + SQS + INMET API) is active.
-- Once enrichment data lands in bronze, join on company location + date to
-- correlate delay_rate_pct with weather events (rain, extreme temperature, etc.).

with order_delays as (
    select
        company_id,
        depositor_id,
        date_trunc('day', issued_at)   as issued_date,
        date_trunc('month', issued_at) as issued_month,
        count(*)                        as order_count,
        avg(
            case
                when delivered_at is not null and issued_at is not null
                then ({{ wms_epoch("delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0
            end
        )                               as avg_cycle_time_hours,
        count(case
            when delivered_at is not null
             and ({{ wms_epoch("delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0 > 48
            then 1
        end)                            as delayed_order_count,
        round(
            count(case
                when delivered_at is not null
                 and ({{ wms_epoch("delivered_at") }} - {{ wms_epoch("issued_at") }}) / 3600.0 > 48
                then 1
            end) * 100.0 / nullif(count(*), 0),
            2
        )                               as delay_rate_pct,
        -- placeholder: will be populated by INMET enrichment JOIN
        cast(null as string)            as weather_condition,
        cast(null as double)            as avg_temperature_c,
        cast(null as double)            as precipitation_mm
    from {{ ref('fct_orders') }}
    where issued_at is not null
    group by 1, 2, 3, 4
)

select * from order_delays

{% if is_incremental() %}
where issued_date > (select max(issued_date) from {{ this }})
{% endif %}
