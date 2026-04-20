with source as (
    select
        cast(SEQUENCIAINTEGRACAO  as {{ dbt.type_string() }})    as order_id,
        cast(SEQUENCIADOCUMENTO   as {{ dbt.type_string() }})    as doc_seq,
        cast(NUMERODOCUMENTO      as {{ dbt.type_string() }})    as document_number,
        cast(SERIEDOCUMENTO       as {{ dbt.type_string() }})    as document_series,
        cast(TIPODOCUMENTO        as {{ dbt.type_string() }})    as document_type,
        cast(CODIGOEMPRESA        as {{ dbt.type_string() }})    as company_id,
        cast(CODIGODEPOSITANTE    as {{ dbt.type_string() }})    as depositor_id,
        cast(DATAEMISSAO          as {{ dbt.type_timestamp() }}) as issued_at,
        cast(DATAENTREGA          as {{ dbt.type_timestamp() }}) as delivered_at,
        cast(VALORTOTALDOCUMENTO  as {{ dbt.type_float() }})     as total_value,
        row_number() over (
            partition by SEQUENCIAINTEGRACAO
            order by SEQUENCIAINTEGRACAO
        ) as _rn
    from {{ source('bronze', 'orders_documento') }}
)

select
    order_id,
    doc_seq,
    document_number,
    document_series,
    document_type,
    company_id,
    depositor_id,
    issued_at,
    delivered_at,
    total_value
from source
where _rn = 1
