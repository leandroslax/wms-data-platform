with source as (
    select
        cast(sequenciaestoque      as {{ dbt.type_string() }})  as inventory_id,
        cast(codigoproduto         as {{ dbt.type_string() }})  as product_id,
        cast(codigoestabelecimento as {{ dbt.type_string() }})  as warehouse_id,
        cast(codigoempresa         as {{ dbt.type_string() }})  as company_id,
        cast(estoqueideal          as {{ dbt.type_int() }})     as ideal_stock_qty,
        cast(estoqueminimo         as {{ dbt.type_int() }})     as min_stock_qty,
        cast(estoquemaximo         as {{ dbt.type_int() }})     as max_stock_qty,
        cast(estoqueseguranca      as {{ dbt.type_int() }})     as safety_stock_qty,
        cast(pontoreposicao        as {{ dbt.type_int() }})     as reorder_point,
        cast(consumomedio          as {{ dbt.type_float() }})   as avg_consumption,
        cast(classeproduto         as {{ dbt.type_string() }})  as product_class,
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
