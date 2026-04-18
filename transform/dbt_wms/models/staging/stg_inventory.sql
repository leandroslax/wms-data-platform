with source as (
    select
        cast(sequenciaestoque      as string) as inventory_id,
        cast(codigoproduto         as string) as product_id,
        cast(codigoestabelecimento as string) as warehouse_id,
        cast(codigoempresa         as string) as company_id,
        cast(estoqueideal          as int)    as ideal_stock_qty,
        cast(estoqueminimo         as int)    as min_stock_qty,
        cast(estoquemaximo         as int)    as max_stock_qty,
        cast(estoqueseguranca      as int)    as safety_stock_qty,
        cast(pontoreposicao        as int)    as reorder_point,
        cast(consumomedio          as double) as avg_consumption,
        cast(classeproduto         as string) as product_class,
        row_number() over (
            partition by sequenciaestoque
            order by sequenciaestoque
        ) as _rn
    from {{ source('bronze', 'inventory_produtoestoque') }}
)

select
    inventory_id,
    product_id,
    warehouse_id,
    company_id,
    ideal_stock_qty,
    min_stock_qty,
    max_stock_qty,
    safety_stock_qty,
    reorder_point,
    avg_consumption,
    product_class
from source
where _rn = 1
