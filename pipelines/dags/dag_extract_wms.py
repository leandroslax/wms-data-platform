"""dag_extract_wms — Extração incremental Oracle WMS → PostgreSQL bronze.

Schedule: diário às 01:00 UTC
Modo: incremental (watermark por tabela, salvo em _watermarks.json)

Tasks:
    check_oracle_conn   → verifica conectividade com Oracle
    extract_incremental → chama oracle_to_postgres.py --mode incremental
    log_summary         → loga contagem de linhas por tabela bronze
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

EXTRACTION_SCRIPT = "/opt/airflow/pipelines/extraction/oracle_to_postgres.py"
WATERMARKS_FILE   = "/opt/airflow/pipelines/extraction/artifacts/_watermarks.json"

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def _check_oracle_conn() -> None:
    """Verifica se Oracle está acessível antes de iniciar extração."""
    import oracledb

    host    = os.environ["ORACLE_HOST"]
    port    = int(os.environ.get("ORACLE_PORT", 1521))
    service = os.environ["ORACLE_SERVICE_NAME"]
    user    = os.environ["ORACLE_USER"]
    pwd     = os.environ["ORACLE_PASSWORD"]

    dsn = oracledb.makedsn(host, port, service_name=service)
    try:
        conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
        conn.close()
        print(f"✅ Oracle conectado: {host}:{port}/{service}")
    except Exception as e:
        raise RuntimeError(f"❌ Oracle inacessível: {e}") from e


def _log_bronze_counts() -> None:
    """Loga contagem de linhas nas tabelas bronze após extração."""
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    tables = [
        "bronze.orders_documento",
        "bronze.movements_entrada_saida",
        "bronze.inventory_produtoestoque",
        "bronze.products_snapshot",
    ]
    with conn.cursor() as cur:
        print("=== Bronze row counts ===")
        for tbl in tables:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            count = cur.fetchone()[0]
            print(f"  {tbl:<45} {count:>10,} rows")
    conn.close()


with DAG(
    dag_id="dag_extract_wms",
    description="Extração incremental Oracle WMS → PostgreSQL bronze",
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 1 * * *",   # 01:00 UTC diário
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["wms", "extraction", "bronze"],
) as dag:

    check_oracle = PythonOperator(
        task_id="check_oracle_conn",
        python_callable=_check_oracle_conn,
    )

    extract = BashOperator(
        task_id="extract_incremental",
        bash_command=(
            f"python {EXTRACTION_SCRIPT} --mode incremental "
            f"--days 2"           # garante sobreposição de 2 dias (reprocessa se falhou ontem)
        ),
        env={
            **{k: os.environ.get(k, "") for k in [
                "ORACLE_HOST", "ORACLE_PORT", "ORACLE_SERVICE_NAME",
                "ORACLE_USER", "ORACLE_PASSWORD",
                "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
                "POSTGRES_USER", "POSTGRES_PASSWORD",
            ]},
        },
    )

    log_counts = PythonOperator(
        task_id="log_bronze_counts",
        python_callable=_log_bronze_counts,
    )

    check_oracle >> extract >> log_counts
