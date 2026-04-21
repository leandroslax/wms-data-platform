"""dag_quality_check — Testes de qualidade dbt sobre os marts gold.

Schedule: disparada quando o dbt conclui a atualização gold
Dependência: evento de dataset emitido por dag_transform_dbt.log_gold_counts

Tasks:
    wait_for_dbt       → aguarda dag_transform_dbt.log_gold_counts completar
    dbt_test           → dbt test --store-failures (falha real se teste quebrar)
    check_row_counts   → valida contagens mínimas esperadas nos marts gold
    check_nulls        → queries de sanidade: NULLs em colunas NOT NULL
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from wms_datasets import DBT_GOLD_REFRESH_DATASET

DBT_PROJECT_DIR  = "/opt/airflow/dbt_wms"
DBT_PROFILES_DIR = "/opt/airflow/dbt_wms"

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

# Contagens mínimas esperadas por mart (alerta se abaixo)
MIN_COUNTS: dict[str, int] = {
    "gold.fct_orders":                1,
    "gold.fct_movements":             1,
    "gold.mart_order_sla":            1,
    "gold.mart_operator_productivity":1,
    "gold.mart_picking_performance":  1,
    "gold.mart_stockout_risk":        1,
    "gold.mart_inventory_health":     1,
}

# Sanidade: nenhuma dessas colunas deve ter NULL
NULL_CHECKS: list[tuple[str, str]] = [
    ("gold.mart_order_sla",            "sla_status"),
    ("gold.mart_stockout_risk",        "risk_level"),
    ("gold.mart_inventory_health",     "stockout_risk"),
    ("gold.mart_operator_productivity","operator_user"),
    ("gold.mart_picking_performance",  "shift"),
    ("gold.fct_orders",                "order_id"),
    ("gold.fct_movements",             "movement_id"),
]


def _check_row_counts() -> None:
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    failures: list[str] = []
    with conn.cursor() as cur:
        print("=== Row count validation ===")
        for tbl, min_count in MIN_COUNTS.items():
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl}")
                count = cur.fetchone()[0]
                status = "OK" if count >= min_count else "FAIL"
                print(f"  [{status}] {tbl:<45} {count:>10,} rows (min={min_count})")
                if count < min_count:
                    failures.append(f"{tbl}: {count} rows < {min_count}")
            except Exception as e:
                print(f"  [ERR] {tbl}: {e}")
                conn.rollback()
                failures.append(f"{tbl}: query error — {e}")
    conn.close()
    if failures:
        raise ValueError(f"Row count check failed:\n" + "\n".join(failures))
    print("✅ All row counts OK")


def _check_nulls() -> None:
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    failures: list[str] = []
    with conn.cursor() as cur:
        print("=== NULL sanity checks ===")
        for tbl, col in NULL_CHECKS:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NULL")
                null_count = cur.fetchone()[0]
                status = "OK" if null_count == 0 else "FAIL"
                print(f"  [{status}] {tbl}.{col}: {null_count} NULLs")
                if null_count > 0:
                    failures.append(f"{tbl}.{col}: {null_count} unexpected NULLs")
            except Exception as e:
                print(f"  [ERR] {tbl}.{col}: {e}")
                conn.rollback()
                failures.append(f"{tbl}.{col}: query error — {e}")
    conn.close()
    if failures:
        raise ValueError("NULL check failed:\n" + "\n".join(failures))
    print("✅ All NULL checks OK")


with DAG(
    dag_id="dag_quality_check",
    description="dbt test + validação de contagens e NULLs nos marts gold",
    start_date=datetime(2026, 1, 1),
    schedule=[DBT_GOLD_REFRESH_DATASET],
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["wms", "quality", "gold"],
) as dag:

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"dbt test "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR} "
            f"--target local "
            f"--store-failures "
            f"--no-use-colors"
            # sem || echo — falha real se o teste quebrar
        ),
        env={
            "DBT_BRONZE_SCHEMA": "bronze",
            "POSTGRES_HOST": os.environ.get("POSTGRES_HOST", "wms-postgres"),
            "POSTGRES_PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "POSTGRES_DB":   os.environ.get("POSTGRES_DB",   "wms"),
            "POSTGRES_USER": os.environ.get("POSTGRES_USER", "wmsadmin"),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "PATH": "/home/airflow/.local/bin:/usr/local/bin:/usr/bin:/bin",
        },
    )

    check_counts = PythonOperator(
        task_id="check_row_counts",
        python_callable=_check_row_counts,
    )

    check_nulls = PythonOperator(
        task_id="check_nulls",
        python_callable=_check_nulls,
    )

    dbt_test >> [check_counts, check_nulls]
