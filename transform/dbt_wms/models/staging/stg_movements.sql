with source as (
    select
        cast(sequenciamovimento    as string)    as movement_id,
        cast(codigoproduto         as string)    as product_id,
        cast(codigoestabelecimento as string)    as warehouse_id,
        cast(codigodepositante     as string)    as depositor_id,
        cast(quantidadeanterior    as int)       as qty_before,
        cast(quantidadeatual       as int)       as qty_after,
        cast(datamovimento         as timestamp) as movement_date,
        cast(estadomovimento       as string)    as movement_status,
        cast(usuario               as string)    as operator_user,
        cast(observacao            as string)    as notes,
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
    movement_date,
    movement_status,
    operator_user,
    notes
from source
where _rn = 1
