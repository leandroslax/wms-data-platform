select
    cast(order_id as string) as order_id,
    cast(customer_id as string) as customer_id,
    cast(product_id as string) as product_id,
    cast(order_status as string) as order_status,
    cast(payment_status as string) as payment_status,
    cast(quantity as int) as quantity,
    cast(total_amount as double) as total_amount,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at
from {{ source('bronze', 'orders') }}
