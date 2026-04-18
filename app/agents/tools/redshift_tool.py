"""Redshift SQL tool for the WMS AnalystAgent.

Connects to Redshift Serverless via credentials from Secrets Manager (prod)
or environment variables (dev/local). Queries the 8 analytical marts.
"""
import json
import os
from typing import Any

import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from crewai.tools import tool


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _get_credentials() -> dict[str, Any]:
    """Resolve Redshift credentials from Secrets Manager or env vars."""
    secret_arn = os.getenv("REDSHIFT_SECRET_ARN")

    if secret_arn:
        client = boto3.client(
            "secretsmanager",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        secret = json.loads(
            client.get_secret_value(SecretId=secret_arn)["SecretString"]
        )
        return {
            "host": secret["host"],
            "port": int(secret.get("port", 5439)),
            "dbname": secret["dbname"],
            "user": secret["username"],
            "password": secret["password"],
        }

    return {
        "host": os.getenv("REDSHIFT_HOST", "localhost"),
        "port": int(os.getenv("REDSHIFT_PORT", 5439)),
        "dbname": os.getenv("REDSHIFT_DB", "wms"),
        "user": os.getenv("REDSHIFT_USER"),
        "password": os.getenv("REDSHIFT_PASSWORD"),
    }


def _connect() -> psycopg2.extensions.connection:
    creds = _get_credentials()
    return psycopg2.connect(**creds, connect_timeout=10)


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

@tool("WMS SQL Analyst")
def redshift_execute_sql(query: str) -> str:
    """Execute SQL against WMS Redshift Serverless for exact analytical data.

    Use when the question requires specific numbers, KPIs, rankings or
    aggregations from the WMS analytical marts. All marts live in the
    'marts' schema in Redshift.

    Available marts:
    - marts.mart_picking_performance
        operator_id, shift, warehouse_id, picks_per_hour, accuracy_rate, date
    - marts.mart_inventory_health
        product_id, warehouse_id, turnover_rate, coverage_days, stockout_risk
    - marts.mart_order_sla
        order_id, company_id, depositor_id, cycle_time_hours, sla_status,
        issued_at, delivered_at
    - marts.mart_operator_productivity
        operator_id, warehouse_id, productivity_score, complexity_index,
        ranking, period
    - marts.mart_stockout_risk
        product_id, warehouse_id, days_to_stockout, risk_level,
        current_stock, avg_daily_consumption
    - marts.mart_geo_performance
        state, city, sla_compliance_rate, avg_cycle_time_hours, order_count
    - marts.mart_geo_inventory
        state, city, coverage_days, stockout_count, product_count
    - marts.mart_weather_impact
        date, city, state, weather_condition, delay_rate, avg_delay_hours,
        order_count

    Args:
        query: Valid SQL SELECT query against the 'marts' schema.
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
