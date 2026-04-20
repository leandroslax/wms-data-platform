# ADR-005: Enriquecimento geográfico inviável na fonte atual

## Status
Aceito

## Contexto
`ORAINT.DOCUMENTO` não registra endereço de entrega:
- `CEPENTREGA`: NULL em 100% dos registros
- `MUNICIPIOENTREGA`: NULL em 100% dos registros
- `UFENTREGA`: NULL em 100% dos registros

## Decisão
Não implementar pipeline ViaCEP/IBGE neste momento.
`mart_geo_performance` agrega por empresa/depositante/mês — sem dimensão geográfica.

## Consequências
- Choropleth map não disponível
- Quando o WMS passar a registrar CEP de entrega, reativar `pipelines/enrichment/`
