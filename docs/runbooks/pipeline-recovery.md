# Pipeline Recovery

Runbook inicial para recuperacao de falhas em extracao, transformacao e carga.

## Checklist

1. Verificar DAG falhada e task raiz.
2. Conferir logs no CloudWatch e no Airflow.
3. Validar checkpoint incremental no bucket de artifacts.
4. Reprocessar janela afetada com deduplicacao validada.
