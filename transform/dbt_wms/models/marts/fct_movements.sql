select
    movement_id,
    product_id,
    order_id,
    movement_type,
    quantity,
    source_location_id,
    target_location_id,
    moved_at,
    ingestion_run_id,
    extraction_timestamp
from {{ ref('stg_movements') }}
