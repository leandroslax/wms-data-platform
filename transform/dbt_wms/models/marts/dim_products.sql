select distinct
    product_id
from {{ ref('stg_orders') }}
where product_id is not null
