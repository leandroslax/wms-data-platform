#!/usr/bin/env python3
"""
superset_setup.py — Configura PostgreSQL + datasets + dashboard no Superset local.

Uso:
    python3 scripts/superset_setup.py

Pré-requisito: Superset rodando em http://localhost:8088
"""
import json
import sys
import time
import requests

BASE_URL = "http://localhost:8088"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

session = requests.Session()


# ─── Auth ─────────────────────────────────────────────────────────────────────

def login():
    r = session.post(f"{BASE_URL}/api/v1/security/login", json={
        "username": ADMIN_USER,
        "password": ADMIN_PASS,
        "provider": "db",
        "refresh": True,
    })
    r.raise_for_status()
    token = r.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})

    # CSRF token
    r2 = session.get(f"{BASE_URL}/api/v1/security/csrf_token/")
    r2.raise_for_status()
    csrf = r2.json()["result"]
    session.headers.update({"X-CSRFToken": csrf, "Referer": BASE_URL})
    print("✅ Autenticado no Superset")


# ─── Database ─────────────────────────────────────────────────────────────────

def create_database():
    # Check if already exists
    r = session.get(f"{BASE_URL}/api/v1/database/", params={"q": json.dumps({"filters": [{"col": "database_name", "opr": "eq", "value": "WMS PostgreSQL"}]})})
    data = r.json()
    if data.get("count", 0) > 0:
        db_id = data["result"][0]["id"]
        print(f"ℹ️  Database já existe (id={db_id})")
        return db_id

    payload = {
        "database_name": "WMS PostgreSQL",
        "sqlalchemy_uri": "postgresql://wmsadmin:wmsadmin2026@wms-postgres:5432/wms",
        "expose_in_sqllab": True,
        "allow_run_async": True,
        "allow_ctas": False,
        "allow_cvas": False,
        "allow_dml": False,
    }
    r = session.post(f"{BASE_URL}/api/v1/database/", json=payload)
    if r.status_code not in (200, 201):
        print(f"❌ Erro ao criar database: {r.status_code} {r.text[:300]}")
        sys.exit(1)
    db_id = r.json()["id"]
    print(f"✅ Database criado (id={db_id})")
    return db_id


# ─── Datasets ─────────────────────────────────────────────────────────────────

TABLES = [
    ("gold", "fct_orders",                  "FCT Orders"),
    ("gold", "fct_movements",               "FCT Movements"),
    ("gold", "mart_order_sla",              "Mart Order SLA"),
    ("gold", "mart_operator_productivity",  "Mart Operator Productivity"),
    ("gold", "mart_picking_performance",    "Mart Picking Performance"),
    ("gold", "mart_stockout_risk",          "Mart Stockout Risk"),
    ("gold", "mart_inventory_health",       "Mart Inventory Health"),
]


def create_datasets(db_id):
    dataset_ids = {}
    for schema, table, label in TABLES:
        # check existing
        r = session.get(f"{BASE_URL}/api/v1/dataset/", params={"q": json.dumps({
            "filters": [
                {"col": "table_name", "opr": "eq", "value": table},
                {"col": "database", "opr": "rel_o_m", "value": db_id},
            ]
        })})
        data = r.json()
        if data.get("count", 0) > 0:
            ds_id = data["result"][0]["id"]
            print(f"ℹ️  Dataset {table} já existe (id={ds_id})")
            dataset_ids[table] = ds_id
            continue

        payload = {
            "database": db_id,
            "schema": schema,
            "table_name": table,
        }
        r = session.post(f"{BASE_URL}/api/v1/dataset/", json=payload)
        if r.status_code not in (200, 201):
            print(f"⚠️  Erro ao criar dataset {table}: {r.status_code} {r.text[:200]}")
            continue
        ds_id = r.json()["id"]
        dataset_ids[table] = ds_id
        print(f"✅ Dataset {table} criado (id={ds_id})")
        time.sleep(0.3)
    return dataset_ids


# ─── Charts ───────────────────────────────────────────────────────────────────

def create_charts(dataset_ids):
    chart_ids = []

    charts = []

    # 1. Orders por status (Big Number)
    if "fct_orders" in dataset_ids:
        charts.append({
            "slice_name": "Total de Pedidos",
            "viz_type": "big_number_total",
            "datasource_id": dataset_ids["fct_orders"],
            "datasource_type": "table",
            "params": json.dumps({
                "metric": {"aggregate": "COUNT", "column": {"column_name": "order_id"}, "expressionType": "SIMPLE", "label": "COUNT(order_id)"},
                "subheader": "pedidos no total",
                "y_axis_format": "SMART_NUMBER",
            }),
        })

    # 2. Movimentações diárias (Line Chart)
    if "fct_movements" in dataset_ids:
        charts.append({
            "slice_name": "Movimentações por Dia",
            "viz_type": "echarts_timeseries_line",
            "datasource_id": dataset_ids["fct_movements"],
            "datasource_type": "table",
            "params": json.dumps({
                "metrics": [{"aggregate": "COUNT", "column": {"column_name": "movement_id"}, "expressionType": "SIMPLE", "label": "Movimentações"}],
                "groupby": [],
                "x_axis": "movement_date",
                "granularity_sqla": "movement_date",
                "time_grain_sqla": "P1D",
                "row_limit": 1000,
                "y_axis_format": "SMART_NUMBER",
                "time_range": "Last 30 days",
                "adhoc_filters": [{
                    "clause": "WHERE",
                    "expressionType": "SQL",
                    "sqlExpression": "movement_date >= CURRENT_DATE - INTERVAL '30 days' AND movement_date < CURRENT_DATE",
                    "subject": None,
                    "operator": None,
                    "comparator": None
                }],
            }),
        })

        charts.append({
            "slice_name": "Movimentações Hoje por Hora",
            "viz_type": "echarts_timeseries_line",
            "datasource_id": dataset_ids["fct_movements"],
            "datasource_type": "table",
            "params": json.dumps({
                "metrics": [{"aggregate": "COUNT", "column": {"column_name": "movement_id"}, "expressionType": "SIMPLE", "label": "Movimentações"}],
                "groupby": [],
                "x_axis": "movement_date",
                "granularity_sqla": "movement_date",
                "time_grain_sqla": "PT1H",
                "row_limit": 1000,
                "y_axis_format": "SMART_NUMBER",
                "time_range": "No filter",
                "adhoc_filters": [{
                    "clause": "WHERE",
                    "expressionType": "SQL",
                    "sqlExpression": "movement_date >= CURRENT_DATE AND movement_date < CURRENT_DATE + INTERVAL '1 day'",
                    "subject": None,
                    "operator": None,
                    "comparator": None
                }],
            }),
        })

    # 3. SLA % on-time (Big Number)
    if "mart_order_sla" in dataset_ids:
        charts.append({
            "slice_name": "SLA — Pedidos no Prazo (%)",
            "viz_type": "big_number_total",
            "datasource_id": dataset_ids["mart_order_sla"],
            "datasource_type": "table",
            "params": json.dumps({
                "metric": {"expressionType": "SQL", "sqlExpression": "ROUND(100.0 * SUM(CASE WHEN sla_met THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1)", "label": "SLA %"},
                "subheader": "% pedidos dentro do prazo",
                "y_axis_format": ".1f",
            }),
        })

    # 4. Top operadores (Table)
    if "mart_operator_productivity" in dataset_ids:
        charts.append({
            "slice_name": "Top Operadores — Produtividade",
            "viz_type": "table",
            "datasource_id": dataset_ids["mart_operator_productivity"],
            "datasource_type": "table",
            "params": json.dumps({
                "metrics": [
                    {"aggregate": "SUM", "column": {"column_name": "total_picks"}, "expressionType": "SIMPLE", "label": "Total Picks"},
                    {"aggregate": "AVG", "column": {"column_name": "picks_per_hour"}, "expressionType": "SIMPLE", "label": "Picks/Hora (média)"},
                ],
                "groupby": ["operator_id"],
                "order_desc": True,
                "row_limit": 20,
                "include_time": False,
            }),
        })

    # 5. Risco de Stockout (Table)
    if "mart_stockout_risk" in dataset_ids:
        charts.append({
            "slice_name": "Risco de Stockout por SKU",
            "viz_type": "table",
            "datasource_id": dataset_ids["mart_stockout_risk"],
            "datasource_type": "table",
            "params": json.dumps({
                "metrics": [
                    {"aggregate": "AVG", "column": {"column_name": "days_of_stock"}, "expressionType": "SIMPLE", "label": "Dias Estoque"},
                    {"aggregate": "AVG", "column": {"column_name": "stockout_risk_score"}, "expressionType": "SIMPLE", "label": "Risk Score"},
                ],
                "groupby": ["product_code"],
                "order_desc": True,
                "row_limit": 20,
                "include_time": False,
            }),
        })

    # 6. Inventory Health (Bar)
    if "mart_inventory_health" in dataset_ids:
        charts.append({
            "slice_name": "Saúde do Inventário — Turnover",
            "viz_type": "echarts_bar",
            "datasource_id": dataset_ids["mart_inventory_health"],
            "datasource_type": "table",
            "params": json.dumps({
                "metrics": [{"aggregate": "AVG", "column": {"column_name": "inventory_turnover"}, "expressionType": "SIMPLE", "label": "Turnover Médio"}],
                "groupby": ["product_code"],
                "order_desc": True,
                "row_limit": 20,
                "y_axis_format": ".2f",
            }),
        })

    for chart in charts:
        r = session.post(f"{BASE_URL}/api/v1/chart/", json=chart)
        if r.status_code not in (200, 201):
            print(f"⚠️  Erro ao criar chart '{chart['slice_name']}': {r.status_code} {r.text[:200]}")
            continue
        cid = r.json()["id"]
        chart_ids.append(cid)
        print(f"✅ Chart '{chart['slice_name']}' criado (id={cid})")
        time.sleep(0.3)

    return chart_ids


# ─── Dashboard ─────────────────────────────────────────────────────────────────

def create_dashboard(chart_ids):
    if not chart_ids:
        print("⚠️  Nenhum chart para adicionar ao dashboard")
        return

    # Build a simple grid layout
    positions = {"DASHBOARD_VERSION_KEY": "v2", "ROOT_ID": {"children": ["GRID_ID"], "id": "ROOT_ID", "type": "ROOT"}, "GRID_ID": {"children": [], "id": "GRID_ID", "type": "GRID"}}

    col = 0
    row = 0
    children = []
    for i, cid in enumerate(chart_ids):
        w = 12 if i == 0 else 6
        if col + w > 24:
            col = 0
            row += 4
        elem_id = f"CHART-{cid}"
        positions[elem_id] = {
            "children": [],
            "id": elem_id,
            "meta": {"chartId": cid, "height": 50, "sliceName": f"Chart {cid}", "width": w},
            "type": "CHART",
        }
        children.append(elem_id)
        col += w

    positions["GRID_ID"]["children"] = children

    payload = {
        "dashboard_title": "WMS Operations",
        "slug": "wms-operations",
        "position_json": json.dumps(positions),
        "published": True,
    }
    r = session.post(f"{BASE_URL}/api/v1/dashboard/", json=payload)
    if r.status_code not in (200, 201):
        print(f"❌ Erro ao criar dashboard: {r.status_code} {r.text[:400]}")
        return

    dash_id = r.json()["id"]
    print(f"✅ Dashboard 'WMS Operations' criado (id={dash_id})")
    print(f"🔗 Acesse: {BASE_URL}/superset/dashboard/{dash_id}/")

    # Attach charts
    r2 = session.put(f"{BASE_URL}/api/v1/dashboard/{dash_id}", json={"json_metadata": json.dumps({"chart_ids": chart_ids})})
    return dash_id


# ─── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Configurando Superset WMS...")
    login()
    db_id = create_database()
    dataset_ids = create_datasets(db_id)
    chart_ids = create_charts(dataset_ids)
    create_dashboard(chart_ids)
    print("\n✅ Pronto! Acesse http://localhost:8088/dashboard/list/")
