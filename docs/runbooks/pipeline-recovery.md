# Pipeline Recovery

Runbook inicial para recuperacao de falhas em extracao, transformacao e carga.

## Checklist

1. Verificar DAG falhada e task raiz.
2. Conferir logs no Airflow, API FastAPI e containers Docker.
3. Validar checkpoint incremental na tabela local de controle ou nos artifacts montados via Docker.
4. Reprocessar janela afetada com deduplicacao validada.
