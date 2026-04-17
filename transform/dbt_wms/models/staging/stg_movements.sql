select
    cast(movement_id as string) as movement_id,
    cast(product_id as string) as product_id,
    cast(order_id as string) as order_id,
    cast(movement_type as string) as movement_type,
    cast(quantity as int) as quantity,
    cast(source_location_id as string) as source_location_id,
    cast(target_location_id as string) as target_location_id,
    cast(moved_at as timestamp) as moved_at,
    cast(ingestion_run_id as string) as ingestion_run_id,
    cast(extraction_timestamp as timestamp) as extraction_timestamp,
    cast(source_system as string) as source_system,
    cast(source_table as string) as source_table
from {{ source('silver', 'movements') }}
