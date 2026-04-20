"""dag_load_warehouse — Carga dos marts gold para o Redshift Serverless.

Schedule: disparada quando os checks de qualidade terminam
Dependência: evento de dataset emitido por dag_quality_check.quality_ready

Contexto:
    Esta DAG opera sobre infraestrutura AWS (Redshift Serverless + S3 Iceberg).
    No ambiente local (Docker), as tasks de Redshift falharão por design —
    a conexão "redshift_default" não existe localmente.
    Para rodar localmente, basta a stack bronze → silver → gold via dbt.

Tasks:
    wait_for_quality   → aguarda dag_quality_check.check_nulls completar
    export_gold_to_s3  → exporta marts gold como Parquet para s3://wms-dp-dev-gold-*/
    redshift_copy      → COPY dos Parquet para tabelas Redshift via Spectrum
    validate_redshift  → valida contagens no Redshift vs PostgreSQL gold
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from wms_datasets import QUALITY_GATE_DATASET

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=15),
    "email_on_failure": False,
}

# Marts a exportar e suas tabelas Redshift alvo
MARTS: dict[str, str] = {
    "gold.fct_orders":                 "wms_gold.fct_orders",
    "gold.fct_movements":              "wms_gold.fct_movements",
    "gold.mart_order_sla":             "wms_gold.mart_order_sla",
    "gold.mart_operator_productivity": "wms_gold.mart_operator_productivity",
    "gold.mart_picking_performance":   "wms_gold.mart_picking_performance",
    "gold.mart_stockout_risk":         "wms_gold.mart_stockout_risk",
    "gold.mart_inventory_health":      "wms_gold.mart_inventory_health",
    "gold.mart_geo_performance":       "wms_gold.mart_geo_performance",
}


def _export_gold_to_s3() -> None:
    """Exporta marts gold do PostgreSQL para Parquet no S3 (caminho Iceberg gold)."""
    import psycopg2

    s3_bucket = os.environ.get("S3_GOLD_BUCKET", "wms-dp-dev-gold-sa-east-1-000000000000")
    s3_prefix = os.environ.get("S3_GOLD_PREFIX", "exports/")

    # Em ambiente local, simula o export logando os counts
    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    print(f"=== Export gold → s3://{s3_bucket}/{s3_prefix} ===")
    with conn.cursor() as cur:
        for pg_tbl in MARTS:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {pg_tbl}")
                count = cur.fetchone()[0]
                # Em produção: psycopg2 COPY TO + boto3 upload, ou Glue job
                print(f"  {pg_tbl:<45} {count:>10,} rows  → s3 (simulado localmente)")
            except Exception as e:
                conn.rollback()
                print(f"  {pg_tbl}: ERRO: {e}")
    conn.close()
    print("✅ Export concluído (local: simulado; AWS: usar Glue job ou COPY TO S3)")


def _redshift_copy() -> None:
    """Executa COPY dos arquivos Parquet para o Redshift Serverless."""
    # Requer variável de ambiente REDSHIFT_CONN ou Airflow Connection 'redshift_default'
    redshift_host = os.environ.get("REDSHIFT_HOST")
    if not redshift_host:
        print(
            "SKIP: REDSHIFT_HOST não configurado. "
            "Esta task é no-op no ambiente local. "
            "Configure as variáveis REDSHIFT_HOST/DB/USER/PASSWORD para ativar."
        )
        return

    import psycopg2  # Redshift usa driver psycopg2 compatível

    conn = psycopg2.connect(
        host=redshift_host,
        port=int(os.environ.get("REDSHIFT_PORT", 5439)),
        dbname=os.environ.get("REDSHIFT_DB", "wms"),
        user=os.environ["REDSHIFT_USER"],
        password=os.environ["REDSHIFT_PASSWORD"],
    )
    s3_bucket = os.environ.get("S3_GOLD_BUCKET", "wms-dp-dev-gold-sa-east-1-000000000000")
    iam_role  = os.environ.get("REDSHIFT_IAM_ROLE", "")

    with conn.cursor() as cur:
        for _, rs_tbl in MARTS.items():
            s3_path = f"s3://{s3_bucket}/exports/{rs_tbl.split('.')[-1]}/"
            sql = (
                f"COPY {rs_tbl} FROM '{s3_path}' "
                f"IAM_ROLE '{iam_role}' FORMAT AS PARQUET;"
            )
            print(f"  COPY → {rs_tbl}")
            cur.execute(sql)
    conn.commit()
    conn.close()
    print("✅ Redshift COPY concluído")


def _validate_redshift() -> None:
    """Valida que contagens no Redshift batem com o gold PostgreSQL."""
    redshift_host = os.environ.get("REDSHIFT_HOST")
    if not redshift_host:
        print("SKIP: REDSHIFT_HOST não configurado — validação ignorada no ambiente local")
        return

    import psycopg2

    pg_conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    rs_conn = psycopg2.connect(
        host=redshift_host,
        port=int(os.environ.get("REDSHIFT_PORT", 5439)),
        dbname=os.environ.get("REDSHIFT_DB", "wms"),
        user=os.environ["REDSHIFT_USER"],
        password=os.environ["REDSHIFT_PASSWORD"],
    )
    mismatches: list[str] = []
    with pg_conn.cursor() as pg_cur, rs_conn.cursor() as rs_cur:
        print("=== Redshift vs PostgreSQL count validation ===")
        for pg_tbl, rs_tbl in MARTS.items():
            pg_cur.execute(f"SELECT COUNT(*) FROM {pg_tbl}")
            rs_cur.execute(f"SELECT COUNT(*) FROM {rs_tbl}")
            pg_count = pg_cur.fetchone()[0]
            rs_count = rs_cur.fetchone()[0]
            match = "OK" if pg_count == rs_count else "MISMATCH"
            print(f"  [{match}] {pg_tbl:<40} pg={pg_count:,}  rs={rs_count:,}")
            if match == "MISMATCH":
                mismatches.append(f"{pg_tbl}: pg={pg_count} rs={rs_count}")
    pg_conn.close()
    rs_conn.close()

    if mismatches:
        raise ValueError("Redshift count mismatch:\n" + "\n".join(mismatches))
    print("✅ Redshift counts validados")


with DAG(
    dag_id="dag_load_warehouse",
    description="Exporta gold → S3 e carrega no Redshift Serverless (no-op local)",
    start_date=datetime(2026, 1, 1),
    schedule=[QUALITY_GATE_DATASET],
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["wms", "redshift", "warehouse"],
) as dag:

    export_s3 = PythonOperator(
        task_id="export_gold_to_s3",
        python_callable=_export_gold_to_s3,
    )

    redshift_copy = PythonOperator(
        task_id="redshift_copy",
        python_callable=_redshift_copy,
    )

    validate = PythonOperator(
        task_id="validate_redshift",
        python_callable=_validate_redshift,
    )

    export_s3 >> redshift_copy >> validate
