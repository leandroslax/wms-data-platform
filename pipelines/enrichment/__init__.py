"""
Geographic and weather enrichment pipeline.

Modules:
    viacep_client   — CEP → city/state/region via ViaCEP REST API
    ibge_client     — static IBGE region/state mapping (no API call)
    weather_client  — historical weather via Open-Meteo (free, no key)
    enrich_geo      — orchestration: maps entity IDs → CEPs → enriches DB
"""
