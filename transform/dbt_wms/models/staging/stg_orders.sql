with source as (
    select
        cast(SEQUENCIADOCUMENTO   as string)    as order_id,
        cast(NUMERODOCUMENTO      as string)    as document_number,
        cast(SERIEDOCUMENTO       as string)    as document_series,
        cast(TIPODOCUMENTO        as string)    as document_type,
        cast(CODIGOEMPRESA        as string)    as company_id,
        cast(CODIGODEPOSITANTE    as string)    as depositor_id,
        cast(DATAEMISSAO          as timestamp) as issued_at,
        cast(DATAENTREGA          as timestamp) as delivered_at,
        cast(VALORTOTALDOCUMENTO  as double)    as total_value,
        cast(SEQUENCIAINTEGRACAO  as string)    as integration_seq,
        row_number() over (
            partition by SEQUENCIADOCUMENTO
            order by SEQUENCIADOCUMENTO
        ) as _rn
    from {{ source('bronze', 'orders_documento') }}
)

select
    order_id,
    document_number,
    document_series,
    document_type,
    company_id,
    depositor_id,
    issued_at,
    delivered_at,
    total_value,
    integration_seq
from source
where _rn = 1
