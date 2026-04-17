select
    cast(movement_id as string) as movement_id,
    cast(product_id as string) as product_id,
    cast(order_id as string) as order_id,
    cast(movement_type as string) as movement_type,
    cast(quantity as int) as quantity,
    cast(source_location_id as string) as source_location_id,
    cast(target_location_id as string) as target_location_id,
    cast(moved_at as timestamp) as moved_at
from {{ source('bronze', 'movements') }}
