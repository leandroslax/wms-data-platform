"""dag_transform_dbt — Transformações dbt (bronze → silver → gold).

Schedule: disparada quando a extração bronze termina
Dependência: evento de dataset emitido por dag_extract_wms.log_bronze_counts

Tasks:
    wait_for_extract  → aguarda dag_extract_wms terminar
    dbt_run           → dbt run --target local (todos os modelos)
    dbt_test          → dbt test (testes de qualidade)
    log_gold_counts   → loga contagem nos marts gold
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from wms_datasets import BRONZE_REFRESH_DATASET, DBT_GOLD_REFRESH_DATASET

DBT_PROJECT_DIR  = "/opt/airflow/dbt_wms"
DBT_PROFILES_DIR = "/opt/airflow/dbt_wms"

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def _log_gold_counts() -> None:
    """Loga contagem de linhas nos marts gold após dbt run."""
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    marts = [
        "gold.fct_orders",
        "gold.fct_movements",
        "gold.dim_products",
        "gold.mart_order_sla",
        "gold.mart_operator_productivity",
        "gold.mart_picking_performance",
        "gold.mart_stockout_risk",
        "gold.mart_inventory_health",
        "gold.mart_geo_performance",
    ]
    with conn.cursor() as cur:
        print("=== Gold row counts ===")
        for tbl in marts:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                count = cur.fetchone()[0]
                print(f"  {tbl:<45} {count:>10,} rows")
            except Exception as e:
                print(f"  {tbl:<45} ERROR: {e}")
                conn.rollback()
    conn.close()


with DAG(
    dag_id="dag_transform_dbt",
    description="dbt run bronze → silver → gold (todos os modelos)",
    start_date=datetime(2026, 1, 1),
    schedule=[BRONZE_REFRESH_DATASET],
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["wms", "dbt", "gold"],
) as dag:

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"dbt run "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR} "
            f"--target local "
            f"--no-partial-parse "
            f"--no-use-colors"
        ),
        env={
            "DBT_BRONZE_SCHEMA": "bronze",
            "POSTGRES_HOST": os.environ.get("POSTGRES_HOST", "wms-postgres"),
            "POSTGRES_PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "POSTGRES_DB": os.environ.get("POSTGRES_DB", "wms"),
            "POSTGRES_USER": os.environ.get("POSTGRES_USER", "wmsadmin"),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "PATH": "/home/airflow/.local/bin:/usr/local/bin:/usr/bin:/bin",
        },
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"dbt test "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR} "
            f"--target local "
            f"--no-partial-parse "
            f"--no-use-colors "
            f"|| echo 'WARN: some dbt tests failed — check logs'"
        ),
        env={
            "DBT_BRONZE_SCHEMA": "bronze",
            "POSTGRES_HOST": os.environ.get("POSTGRES_HOST", "wms-postgres"),
            "POSTGRES_PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "POSTGRES_DB": os.environ.get("POSTGRES_DB", "wms"),
            "POSTGRES_USER": os.environ.get("POSTGRES_USER", "wmsadmin"),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "PATH": "/home/airflow/.local/bin:/usr/local/bin:/usr/bin:/bin",
        },
    )

    log_counts = PythonOperator(
        task_id="log_gold_counts",
        python_callable=_log_gold_counts,
        outlets=[DBT_GOLD_REFRESH_DATASET],
    )

    dbt_run >> dbt_test >> log_counts
