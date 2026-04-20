with source as (
    select
        cast(sequenciamovimento    as {{ dbt.type_string() }})    as movement_id,
        cast(codigoproduto         as {{ dbt.type_string() }})    as product_id,
        cast(codigoestabelecimento as {{ dbt.type_string() }})    as warehouse_id,
        cast(codigodepositante     as {{ dbt.type_string() }})    as depositor_id,
        cast(quantidadeanterior    as {{ dbt.type_int() }})       as qty_before,
        cast(quantidadeatual       as {{ dbt.type_int() }})       as qty_after,
        cast(datamovimento         as {{ dbt.type_timestamp() }}) as movement_date,
        cast(estadomovimento       as {{ dbt.type_string() }})    as movement_status,
        cast(usuario               as {{ dbt.type_string() }})    as operator_user,
        cast(observacao            as {{ dbt.type_string() }})    as notes,
        row_number() over (
            partition by sequenciamovimento
            order by sequenciamovimento
        ) as _rn
    from {{ source('bronze', 'movements_entrada_saida') }}
)

select
    movement_id,
    product_id,
    warehouse_id,
    depositor_id,
    qty_before,
    qty_after,
    qty_after - qty_before as qty_delta,
    movement_date,
    movement_status,
    operator_user,
    notes
from source
where _rn = 1
