select
    cast(inventory_id as string) as inventory_id,
    cast(product_id as string) as product_id,
    cast(warehouse_id as string) as warehouse_id,
    cast(location_id as string) as location_id,
    cast(on_hand_qty as int) as on_hand_qty,
    cast(allocated_qty as int) as allocated_qty,
    cast(available_qty as int) as available_qty,
    cast(snapshot_at as timestamp) as snapshot_at
from {{ source('bronze', 'inventory') }}
