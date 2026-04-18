{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        file_format='iceberg',
        unique_key=['operator_user', 'warehouse_id', 'shift_date', 'shift']
    )
}}

-- Picking performance from outbound movements (qty_delta < 0).
-- Shift approximated by movement_date hour:
--   morning: 06–13h | afternoon: 14–21h | night: 22–05h

with picking_events as (
    select
        operator_user,
        warehouse_id,
        product_id,
        abs(qty_delta)                       as qty_picked,
        movement_date,
        date_trunc('day', movement_date)     as shift_date,
        case
            when hour(movement_date) between 6  and 13 then 'morning'
            when hour(movement_date) between 14 and 21 then 'afternoon'
            else                                            'night'
        end as shift
    from {{ ref('fct_movements') }}
    where qty_delta < 0
      and operator_user is not null
      and movement_date is not null
),

aggregated as (
    select
        operator_user,
        warehouse_id,
        shift_date,
        shift,
        count(*)                    as picks_count,
        sum(qty_picked)             as total_qty_picked,
        count(distinct product_id)  as distinct_skus_picked,
        min(movement_date)          as shift_start,
        max(movement_date)          as shift_end
    from picking_events
    group by 1, 2, 3, 4
),

with_rates as (
    select
        *,
        round(
            (unix_timestamp(shift_end) - unix_timestamp(shift_start)) / 3600.0,
            2
        ) as active_hours,
        case
            when unix_timestamp(shift_end) > unix_timestamp(shift_start)
            then round(
                picks_count /
                ((unix_timestamp(shift_end) - unix_timestamp(shift_start)) / 3600.0),
                2
            )
            else null
        end as picks_per_hour
    from aggregated
)

select * from with_rates

{% if is_incremental() %}
where shift_date > (select max(shift_date) from {{ this }})
{% endif %}
