# Infrastructure Boundaries

## Local Docker services

- PostgreSQL (bronze / silver / gold schemas)
- Airflow scheduler + webserver
- Grafana dashboards
- Qdrant vector store

## External connections

- Oracle WMS: read-only via cx_Oracle (private host)
- Public enrichment APIs: ViaCEP, IBGE, Open-Meteo, ANTT

## Security boundaries

- Credentials in `.env` (never committed)
- Oracle access is read-only
- API protected by API Key
- Gitleaks pre-commit hook prevents secrets in code

## Design rule

Keep data processing local, expose only the FastAPI edge, and isolate credentials via environment variables.
