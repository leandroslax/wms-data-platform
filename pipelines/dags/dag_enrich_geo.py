"""dag_enrich_geo — Enriquecimento geográfico e climático do WMS.

Schedule: semanal (toda segunda-feira às 03:00 UTC)
Fonte geo: ViaCEP REST API (gratuito, sem chave)
Fonte clima: Open-Meteo Archive API (gratuito, sem chave)

Tasks:
    check_db_tables      → valida existência de bronze.geo_reference e bronze.weather_daily
    enrich_geo_refs      → resolve CEPs via ViaCEP, upserta bronze.geo_reference
    enrich_weather       → busca clima histórico (30 dias) via Open-Meteo, upserta bronze.weather_daily
    log_summary          → loga contagens pós-enriquecimento

Dependências do ENTITY_CEP_MAP (mapeamento estático warehouse/company → CEP):
    pipelines/enrichment/enrich_geo.py — ENTITY_CEP_MAP
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import psycopg2
from airflow import DAG
from airflow.operators.python import PythonOperator

from pipelines.enrichment.enrich_geo import enrich_geo_references, enrich_weather

logger = logging.getLogger(__name__)

WEATHER_LOOK_BACK_DAYS = int(os.getenv("GEO_WEATHER_DAYS", "30"))

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def _db_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "wms"),
        user=os.getenv("POSTGRES_USER", "wmsadmin"),
        password=os.getenv("POSTGRES_PASSWORD", "wmsadmin2026"),
    )


# ── Task functions ──────────────────────────────────────────────────────────

def check_db_tables(**_):
    """Ensure the enrichment tables exist before writing."""
    required_tables = ["bronze.geo_reference", "bronze.weather_daily"]
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            for full_table in required_tables:
                schema, table = full_table.split(".")
                cur.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_name = %s",
                    (schema, table),
                )
                if not cur.fetchone():
                    raise RuntimeError(
                        f"Tabela {full_table} não encontrada. "
                        "Execute o init.sql para criá-la."
                    )
        logger.info("Tabelas de enriquecimento verificadas com sucesso")
    finally:
        conn.close()


def run_enrich_geo_refs(**_):
    """Resolve entity CEPs via ViaCEP and upsert into bronze.geo_reference."""
    rows = enrich_geo_references(dry_run=False)
    logger.info("geo_reference: %d entidades enriquecidas", len(rows))
    return len(rows)


def run_enrich_weather(**_):
    """Fetch historical weather via Open-Meteo and upsert bronze.weather_daily."""
    count = enrich_weather(weather_days=WEATHER_LOOK_BACK_DAYS, dry_run=False)
    logger.info("weather_daily: %d registros upsertados (%d dias)", count, WEATHER_LOOK_BACK_DAYS)
    return count


def log_summary(**_):
    """Log row counts from the enrichment tables."""
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bronze.geo_reference")
            geo_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM bronze.weather_daily")
            weather_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(DISTINCT location_uf) FROM bronze.weather_daily"
            )
            uf_count = cur.fetchone()[0]

        logger.info(
            "Resumo pós-enriquecimento — geo_reference: %d linhas | "
            "weather_daily: %d dias × %d UFs",
            geo_count, weather_count, uf_count,
        )
    finally:
        conn.close()


# ── DAG definition ──────────────────────────────────────────────────────────

with DAG(
    dag_id="enrich_geo",
    description="Enriquecimento geográfico e climático (ViaCEP + Open-Meteo)",
    schedule_interval="0 3 * * 1",  # toda segunda às 03:00 UTC
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["enrichment", "geo", "weather", "bronze"],
    doc_md=__doc__,
) as dag:

    t_check = PythonOperator(
        task_id="check_db_tables",
        python_callable=check_db_tables,
    )

    t_geo = PythonOperator(
        task_id="enrich_geo_refs",
        python_callable=run_enrich_geo_refs,
    )

    t_weather = PythonOperator(
        task_id="enrich_weather",
        python_callable=run_enrich_weather,
    )

    t_summary = PythonOperator(
        task_id="log_summary",
        python_callable=log_summary,
    )

    t_check >> t_geo >> t_weather >> t_summary
