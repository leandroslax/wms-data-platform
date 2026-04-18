{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['operator_user', 'warehouse_id', 'period_date']
    )
}}

-- Operator productivity based on movement volume.
-- Tasks extractor (operators.py) is pending — once available, enrich with
-- task counts, error rates and complexity weights per task type.

with daily_ops as (
    select
        operator_user,
        warehouse_id,
        date_trunc('day', movement_date)          as period_date,
        count(*)                                   as movement_count,
        sum(abs(qty_delta))                        as total_qty_handled,
        count(case when qty_delta < 0 then 1 end) as outbound_count,
        count(case when qty_delta > 0 then 1 end) as inbound_count,
        count(distinct product_id)                 as distinct_skus
    from {{ ref('fct_movements') }}
    where operator_user is not null
      and movement_date is not null
    group by 1, 2, 3
),

with_scores as (
    select
        *,
        -- outbound movements weighted 1.5x (picking is more complex than receiving)
        round(
            (outbound_count * 1.5 + inbound_count) / nullif(movement_count, 0),
            3
        ) as complexity_index,
        -- productivity score: total qty handled per movement (efficiency proxy)
        round(total_qty_handled / nullif(movement_count, 0), 2) as avg_qty_per_move,
        rank() over (
            partition by warehouse_id, period_date
            order by movement_count desc
        ) as daily_ranking
    from daily_ops
)

select * from with_scores

{% if is_incremental() %}
where period_date > (select max(period_date) from {{ this }})
{% endif %}
