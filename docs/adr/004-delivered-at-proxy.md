# ADR-004: Tratamento de delivered_at ausente no Oracle WMS

## Status
Aceito

## Contexto
`ORAINT.DOCUMENTO` não registra data de entrega/conclusão real:
- `DATAENTREGA`: NULL em 100% dos registros
- `DATAMOVIMENTO`: NULL nos últimos 90 dias
- `NFEDATAAUTORIZACAO`: NULL em 100% dos registros recentes
- Não existe join direto confiável entre `WMAS.MOVIMENTOENTRADASAIDA` e `ORAINT.DOCUMENTO`

## Decisão
Manter `delivered_at = NULL` no `fct_orders` como representação fiel da fonte.
`mart_order_sla` classifica corretamente esses pedidos como `pending`.

Não usar proxies não confiáveis (última movimentação por produto/armazém não
garante correspondência 1:1 com o documento).

## Consequências
- `mart_order_sla` mostra todos os pedidos como `pending` — comportamento correto
- SLA real só será calculável quando o Oracle WMS registrar datas de entrega
- Monitorar via `dag_quality_check`: alertar se % pending > 95% por mais de 30 dias
