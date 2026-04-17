select
    order_id,
    customer_id,
    product_id,
    order_status,
    payment_status,
    quantity,
    total_amount,
    created_at,
    updated_at
from {{ ref('stg_orders') }}
