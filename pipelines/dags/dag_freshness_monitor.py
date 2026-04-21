"""dag_freshness_monitor — Monitora frescor dos dados em todas as camadas.

Schedule: horário (a cada 1h)
Sem dependência de sensor — roda independente para alertar cedo.

Tasks:
    check_bronze_freshness → verifica _cdc_loaded_at nas tabelas bronze
                             (alerta se alguma tabela não foi atualizada em > 26h)
    check_gold_freshness   → verifica se os marts gold refletem dados recentes
                             (fct_orders.issued_at, fct_movements.movement_date)
    log_freshness_summary  → loga resumo com timestamps de cada camada
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-engineering",
    "retries": 0,          # monitor não faz retry — se falhou, alerta já foi emitido
    "email_on_failure": False,
}

# Tabelas bronze e o SLA de frescor em horas
BRONZE_FRESHNESS: dict[str, int] = {
    "bronze.orders_documento":         26,   # extração diária + margem de 2h
    "bronze.movements_entrada_saida":  26,
    "bronze.inventory_produtoestoque": 26,
    "bronze.products_snapshot":        26,
}

# Colunas de negócio para verificar data mais recente no gold
GOLD_RECENCY: list[tuple[str, str, int]] = [
    # (tabela, coluna_data, max_dias_sem_dado_novo)
    ("gold.fct_orders",    "issued_at",     2),
    ("gold.fct_movements", "movement_date", 2),
]


def _check_bronze_freshness() -> None:
    """Alerta se alguma tabela bronze não recebeu dados em mais de SLA horas."""
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    warnings: list[str] = []
    with conn.cursor() as cur:
        print("=== Bronze freshness ===")
        for tbl, sla_hours in BRONZE_FRESHNESS.items():
            try:
                cur.execute(
                    f"SELECT MAX(_cdc_loaded_at), COUNT(*) FROM {tbl}"
                )
                row = cur.fetchone()
                last_load, total = row[0], row[1]

                if last_load is None:
                    print(f"  [WARN] {tbl}: nenhum dado (tabela vazia)")
                    warnings.append(f"{tbl}: empty")
                    continue

                # torna offset-aware para comparar com now() UTC-aware
                from datetime import timezone
                now_utc = datetime.now(timezone.utc)
                if last_load.tzinfo is None:
                    last_load = last_load.replace(tzinfo=timezone.utc)

                age_hours = (now_utc - last_load).total_seconds() / 3600
                status = "OK" if age_hours <= sla_hours else "STALE"
                print(
                    f"  [{status}] {tbl:<45} "
                    f"last={last_load.strftime('%Y-%m-%d %H:%M')} "
                    f"age={age_hours:.1f}h  rows={total:,}"
                )
                if status == "STALE":
                    warnings.append(
                        f"{tbl}: last load {age_hours:.1f}h ago (SLA={sla_hours}h)"
                    )
            except Exception as e:
                print(f"  [ERR] {tbl}: {e}")
                conn.rollback()
    conn.close()

    if warnings:
        # Não levanta exceção — freshness é alerta, não bloqueio do pipeline
        print("\n⚠️  FRESHNESS WARNINGS:\n" + "\n".join(f"  • {w}" for w in warnings))
    else:
        print("✅ All bronze tables within freshness SLA")


def _check_gold_freshness() -> None:
    """Verifica se os fatos gold contêm dados recentes de negócio."""
    import psycopg2
    from datetime import timezone

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    warnings: list[str] = []
    with conn.cursor() as cur:
        print("=== Gold recency ===")
        for tbl, col, max_days in GOLD_RECENCY:
            try:
                cur.execute(f"SELECT MAX({col}), COUNT(*) FROM {tbl}")
                row = cur.fetchone()
                latest, total = row[0], row[1]

                if latest is None:
                    print(f"  [WARN] {tbl}.{col}: no data")
                    warnings.append(f"{tbl}.{col}: no data")
                    continue

                now_utc = datetime.now(timezone.utc)
                if hasattr(latest, 'tzinfo') and latest.tzinfo is None:
                    latest = latest.replace(tzinfo=timezone.utc)

                age_days = (now_utc - latest).total_seconds() / 86400
                status = "OK" if age_days <= max_days else "STALE"
                print(
                    f"  [{status}] {tbl}.{col:<30} "
                    f"latest={latest.strftime('%Y-%m-%d')} "
                    f"age={age_days:.1f}d  rows={total:,}"
                )
                if status == "STALE":
                    warnings.append(
                        f"{tbl}.{col}: latest data {age_days:.1f} days ago (max={max_days}d)"
                    )
            except Exception as e:
                print(f"  [ERR] {tbl}.{col}: {e}")
                conn.rollback()
    conn.close()

    if warnings:
        print("\n⚠️  GOLD RECENCY WARNINGS:\n" + "\n".join(f"  • {w}" for w in warnings))
    else:
        print("✅ All gold facts contain recent data")


def _log_freshness_summary() -> None:
    """Loga um sumário compacto de frescor para o painel Grafana/Airflow."""
    import psycopg2
    from datetime import timezone

    conn = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )
    now_utc = datetime.now(timezone.utc)
    print(f"\n{'='*60}")
    print(f"  Freshness summary @ {now_utc.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    queries = {
        "orders_bronze":  "SELECT COUNT(*), MAX(_cdc_loaded_at) FROM bronze.orders_documento",
        "movements_bronze":"SELECT COUNT(*), MAX(_cdc_loaded_at) FROM bronze.movements_entrada_saida",
        "orders_gold":    "SELECT COUNT(*), MAX(issued_at)       FROM gold.fct_orders",
        "movements_gold": "SELECT COUNT(*), MAX(movement_date)   FROM gold.fct_movements",
        "mart_sla":       "SELECT COUNT(*), MAX(issued_at)       FROM gold.mart_order_sla",
    }
    with conn.cursor() as cur:
        for label, sql in queries.items():
            try:
                cur.execute(sql)
                count, latest = cur.fetchone()
                ts = latest.strftime('%Y-%m-%d %H:%M') if latest else 'N/A'
                print(f"  {label:<20} rows={count:>10,}  latest={ts}")
            except Exception as e:
                conn.rollback()
                print(f"  {label:<20} ERROR: {e}")
    conn.close()
    print(f"{'='*60}\n")


with DAG(
    dag_id="dag_freshness_monitor",
    description="Monitora frescor dos dados bronze → gold (alerta sem bloquear)",
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 * * * *",   # toda hora
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["wms", "monitoring", "freshness"],
) as dag:

    bronze_check = PythonOperator(
        task_id="check_bronze_freshness",
        python_callable=_check_bronze_freshness,
    )

    gold_check = PythonOperator(
        task_id="check_gold_freshness",
        python_callable=_check_gold_freshness,
    )

    summary = PythonOperator(
        task_id="log_freshness_summary",
        python_callable=_log_freshness_summary,
    )

    [bronze_check, gold_check] >> summary
