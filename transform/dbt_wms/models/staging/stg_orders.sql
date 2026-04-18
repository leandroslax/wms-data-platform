with source as (
    select
        cast(SEQUENCIADOCUMENTO   as {{ dbt.type_string() }})    as order_id,
        cast(NUMERODOCUMENTO      as {{ dbt.type_string() }})    as document_number,
        cast(SERIEDOCUMENTO       as {{ dbt.type_string() }})    as document_series,
        cast(TIPODOCUMENTO        as {{ dbt.type_string() }})    as document_type,
        cast(CODIGOEMPRESA        as {{ dbt.type_string() }})    as company_id,
        cast(CODIGODEPOSITANTE    as {{ dbt.type_string() }})    as depositor_id,
        cast(DATAEMISSAO          as {{ dbt.type_timestamp() }}) as issued_at,
        cast(DATAENTREGA          as {{ dbt.type_timestamp() }}) as delivered_at,
        cast(VALORTOTALDOCUMENTO  as {{ dbt.type_float() }})     as total_value,
        cast(SEQUENCIAINTEGRACAO  as {{ dbt.type_string() }})    as integration_seq,
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
