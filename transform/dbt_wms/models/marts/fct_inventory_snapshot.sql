select
    inventory_id,
    product_id,
    warehouse_id,
    location_id,
    on_hand_qty,
    allocated_qty,
    available_qty,
    snapshot_at
from {{ ref('stg_inventory') }}
