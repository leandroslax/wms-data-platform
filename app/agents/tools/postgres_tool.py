"""PostgreSQL SQL tool for the WMS AnalystAgent.

Connects to the local PostgreSQL instance and queries the 8 analytical
marts in the 'gold' schema. Credentials resolved from environment variables.
"""
import json
import os
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from crewai.tools import tool


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def _connect() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "wms"),
        user=os.getenv("POSTGRES_USER", "wmsadmin"),
        password=os.getenv("POSTGRES_PASSWORD", "wmsadmin2026"),
        connect_timeout=10,
        options="-c search_path=gold,public",
    )


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

@tool("WMS SQL Analyst")
def postgres_execute_sql(query: str) -> str:
    """Execute SQL against WMS PostgreSQL for exact analytical data.

    Use when the question requires specific numbers, KPIs, rankings or
    aggregations from the WMS analytical marts. All marts live in the
    'gold' schema.

    Available marts:
    - gold.mart_picking_performance
        operator_user, warehouse_id, shift_date, shift,
        picks_count, total_qty_picked, distinct_skus_picked,
        active_hours, picks_per_hour
    - gold.mart_inventory_health
        inventory_id, product_id, warehouse_id, company_id, product_class,
        coverage_days, stock_utilization_rate, stockout_risk,
        below_safety_stock, below_reorder_point
    - gold.mart_order_sla
        order_id, company_id, depositor_id, doc_type,
        cycle_time_hours, sla_status, issued_at, delivered_at
    - gold.mart_operator_productivity
        operator_user, period_date, warehouse_id,
        total_movements, total_qty_moved, distinct_products,
        distinct_warehouses, active_days
    - gold.mart_stockout_risk
        inventory_id, product_id, warehouse_id, company_id, product_class,
        current_stock, avg_daily_consumption, days_to_stockout,
        risk_level, snapshot_date
    - gold.mart_geo_performance
        company_id, depositor_id, issued_month,
        order_count, avg_cycle_time_hours, delayed_order_count, delay_rate_pct
    - gold.mart_geo_inventory
        warehouse_id, company_id, product_class,
        product_count, avg_coverage_days, stockout_count, stock_health_pct
    - gold.mart_weather_impact
        company_id, depositor_id, issued_date, issued_month,
        order_count, avg_cycle_time_hours, delayed_order_count, delay_rate_pct

    Args:
        query: Valid SQL SELECT query. Use schema prefix 'gold.' or rely on
               search_path already set to gold.
    """
    try:
        conn = _connect()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            rows = cur.fetchmany(50)
        conn.close()

        if not rows:
            return "Query executada com sucesso — nenhum resultado retornado."

        return json.dumps(
            [dict(r) for r in rows],
            default=str,
            ensure_ascii=False,
            indent=2,
        )

    except psycopg2.Error as e:
        return f"Erro SQL: {e.pgerror or str(e)}"
    except Exception as e:
        return f"Erro inesperado: {e}"
