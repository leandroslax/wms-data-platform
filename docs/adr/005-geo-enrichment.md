# ADR-005: Enriquecimento geográfico sintético para dashboards de demonstração

## Status
Aceito

## Contexto
`ORAINT.DOCUMENTO` não registra endereço de entrega:
- `CEPENTREGA`: NULL em 100% dos registros
- `MUNICIPIOENTREGA`: NULL em 100% dos registros
- `UFENTREGA`: NULL em 100% dos registros

## Decisão
Implementar enriquecimento geográfico sintético no ambiente local para demo.

O pipeline `dag_enrich_geo` passa a:
- identificar IDs reais de `warehouse`, `company` e `depositor` já presentes no banco
- atribuir CEPs fictícios de forma determinística
- derivar cidade, estado, região e coordenadas representativas para visualização
- popular `bronze.geo_reference` e `bronze.weather_daily` para uso nos dashboards

`mart_geo_performance`, `mart_geo_inventory` e `mart_weather_impact` continuam válidos
como visão analítica de demonstração, mas não representam geografia real de entrega.

## Consequências
- O dashboard geográfico fica funcional no ambiente local
- Mapas e análises por UF/região passam a usar dados sintéticos, não operacionais reais
- Toda comunicação deve deixar explícito que a geografia é de demonstração
- Quando o WMS passar a registrar CEP de entrega, o enriquecimento sintético deve ser substituído por dado real
