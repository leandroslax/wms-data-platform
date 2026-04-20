#!/usr/bin/env python3
"""
Reconstrói o Superset WMS do zero com charts robustos usando dados reais.
Roda via: docker exec -i wms-superset python3 < scripts/superset_rebuild.py
"""
import json, sqlite3

DB = "/app/superset_home/superset.db"
con = sqlite3.connect(DB)
cur = con.cursor()

# ── Limpa estado anterior ─────────────────────────────────────────────────────
cur.execute("DELETE FROM dashboard_slices")
cur.execute("DELETE FROM slices")
cur.execute("DELETE FROM dashboards")
con.commit()
print("Limpeza feita")

# ── Dataset IDs já existem ────────────────────────────────────────────────────
ds = {r[1]: r[0] for r in cur.execute("SELECT id, table_name FROM tables")}
print(f"Datasets: {ds}")

# ── Helper ────────────────────────────────────────────────────────────────────
def add_chart(name, viz, table_name, params):
    if table_name not in ds:
        print(f"  SKIP '{table_name}' não encontrado -> {name}")
        return None
    cur.execute(
        "INSERT INTO slices (slice_name, viz_type, datasource_id, datasource_type, params, created_by_fk, changed_by_fk, created_on, changed_on) VALUES (?,?,?,?,?,1,1,datetime('now'),datetime('now'))",
        (name, viz, ds[table_name], "table", json.dumps(params))
    )
    sid = cur.lastrowid
    print(f"  OK [{viz}] {name} (id={sid})")
    return sid

# ──────────────────────────────────────────────────────────────────────────────
# CHARTS
# ──────────────────────────────────────────────────────────────────────────────
chart_ids = []

for args in [
    # 1. KPIs
    ("Total de Pedidos", "big_number_total", "fct_orders", {
        "metric": {"aggregate":"COUNT","column":{"column_name":"order_id"},"expressionType":"SIMPLE","label":"Pedidos"},
        "subheader": "pedidos no total", "y_axis_format": "SMART_NUMBER",
        "granularity_sqla": "issued_at", "time_range": "No filter",
    }),
    ("Total de Movimentos", "big_number_total", "fct_movements", {
        "metric": {"aggregate":"COUNT","column":{"column_name":"movement_id"},"expressionType":"SIMPLE","label":"Movimentos"},
        "subheader": "movimentos registrados", "y_axis_format": "SMART_NUMBER",
        "granularity_sqla": "movement_date", "time_range": "No filter",
    }),
    # COALESCE garante 0 quando todos os pedidos ainda são 'pending'
    ("SLA % no Prazo", "big_number_total", "mart_order_sla", {
        "metric": {
            "expressionType": "SQL",
            "sqlExpression": "COALESCE(ROUND(100.0*SUM(CASE WHEN sla_status IN ('on_time_express','on_time') THEN 1 ELSE 0 END)/NULLIF(SUM(CASE WHEN sla_status!='pending' THEN 1 ELSE 0 END),0),1), 0)",
            "label": "SLA %",
        },
        "subheader": "% pedidos no prazo", "y_axis_format": ".1f",
        "granularity_sqla": "issued_at", "time_range": "No filter",
    }),
    ("Pedidos em Aberto", "big_number_total", "mart_order_sla", {
        "metric": {
            "expressionType": "SQL",
            "sqlExpression": "SUM(CASE WHEN sla_status='pending' THEN 1 ELSE 0 END)",
            "label": "Em Aberto",
        },
        "subheader": "aguardando entrega", "y_axis_format": "SMART_NUMBER",
        "granularity_sqla": "issued_at", "time_range": "No filter",
    }),

    # 2. Linha do tempo + Pie
    ("Movimentacoes por Dia", "echarts_timeseries_line", "fct_movements", {
        "metrics": [{"aggregate":"COUNT","column":{"column_name":"movement_id"},"expressionType":"SIMPLE","label":"Movimentacoes"}],
        "x_axis": "movement_date", "time_grain_sqla": "P1D",
        "row_limit": 500, "y_axis_format": "SMART_NUMBER", "rich_tooltip": True,
    }),
    ("SLA por Status", "pie", "mart_order_sla", {
        "metric": {"aggregate":"COUNT","column":{"column_name":"order_id"},"expressionType":"SIMPLE","label":"Pedidos"},
        "groupby": ["sla_status"], "row_limit": 10,
        "donut": True, "show_labels": True, "show_legend": True,
    }),

    # 3. Tabelas operacionais
    ("Volume de Pedidos por Mes", "table", "mart_order_sla", {
        "metrics": [
            {"aggregate":"COUNT","column":{"column_name":"order_id"},"expressionType":"SIMPLE","label":"Pedidos"},
            {"expressionType":"SQL","sqlExpression":"ROUND(SUM(total_value)::numeric,2)","label":"Valor Total"},
            {"expressionType":"SQL","sqlExpression":"COALESCE(ROUND(100.0*SUM(CASE WHEN sla_status IN ('on_time_express','on_time') THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1),0)","label":"SLA %"},
        ],
        "groupby": ["issued_month","company_id"], "order_desc": True,
        "row_limit": 24, "include_time": False,
    }),
    ("Pedidos por Tipo de Documento", "table", "fct_orders", {
        "metrics": [
            {"aggregate":"COUNT","column":{"column_name":"order_id"},"expressionType":"SIMPLE","label":"Qtd"},
            {"expressionType":"SQL","sqlExpression":"ROUND(AVG(total_value)::numeric,2)","label":"Valor Medio"},
            {"expressionType":"SQL","sqlExpression":"ROUND(SUM(total_value)::numeric,2)","label":"Valor Total"},
        ],
        "groupby": ["document_type","company_id"], "order_desc": True,
        "row_limit": 20, "include_time": False,
    }),

    # 4. Operadores
    ("Top Operadores - Produtividade", "table", "mart_operator_productivity", {
        "metrics": [
            {"aggregate":"SUM","column":{"column_name":"movement_count"},"expressionType":"SIMPLE","label":"Movimentos"},
            {"aggregate":"AVG","column":{"column_name":"avg_qty_per_move"},"expressionType":"SIMPLE","label":"Qtd/Mov"},
            {"aggregate":"AVG","column":{"column_name":"complexity_index"},"expressionType":"SIMPLE","label":"Complexidade"},
        ],
        "groupby": ["operator_user","warehouse_id"], "order_desc": True,
        "row_limit": 20, "include_time": False,
    }),
    # Nota: echarts_bar categorico instavel no Superset 3.1 → table ordenada como alternativa
    ("Ranking Operadores Top 15", "table", "mart_operator_productivity", {
        "metrics": [
            {"aggregate":"SUM","column":{"column_name":"movement_count"},"expressionType":"SIMPLE","label":"Movimentos"},
            {"aggregate":"AVG","column":{"column_name":"avg_qty_per_move"},"expressionType":"SIMPLE","label":"Qtd/Mov"},
            {"aggregate":"MAX","column":{"column_name":"outbound_count"},"expressionType":"SIMPLE","label":"Saidas Max"},
        ],
        "groupby": ["operator_user"], "order_desc": True,
        "row_limit": 15, "include_time": False, "time_range": "No filter",
    }),

    # 5. Estoque
    ("Risco de Stockout por Produto", "table", "mart_stockout_risk", {
        "metrics": [
            {"aggregate":"AVG","column":{"column_name":"current_stock"},"expressionType":"SIMPLE","label":"Estoque Atual"},
            {"aggregate":"AVG","column":{"column_name":"avg_daily_consumption"},"expressionType":"SIMPLE","label":"Consumo/Dia"},
            {"aggregate":"AVG","column":{"column_name":"days_to_stockout"},"expressionType":"SIMPLE","label":"Dias ate Ruptura"},
        ],
        "groupby": ["product_id","warehouse_id","risk_level"], "order_desc": False,
        "row_limit": 20, "include_time": False,
    }),
    ("Distribuicao de Risco de Estoque", "pie", "mart_stockout_risk", {
        "metric": {"aggregate":"COUNT","column":{"column_name":"inventory_id"},"expressionType":"SIMPLE","label":"SKUs"},
        "groupby": ["risk_level"], "row_limit": 10,
        "donut": True, "show_labels": True, "show_legend": True,
    }),
    ("Saude do Inventario", "table", "mart_inventory_health", {
        "metrics": [
            {"aggregate":"AVG","column":{"column_name":"min_stock_qty"},"expressionType":"SIMPLE","label":"Estoque Min"},
            {"aggregate":"AVG","column":{"column_name":"coverage_days"},"expressionType":"SIMPLE","label":"Cobertura (dias)"},
            {"aggregate":"AVG","column":{"column_name":"stock_utilization_rate"},"expressionType":"SIMPLE","label":"Utilizacao %"},
        ],
        "groupby": ["product_id","warehouse_id","stockout_risk"], "order_desc": False,
        "row_limit": 20, "include_time": False,
    }),

    # 6. Picking — colunas verificadas: picks_count, picks_per_hour, total_qty_picked, distinct_skus_picked
    ("Performance de Picking por Turno", "table", "mart_picking_performance", {
        "metrics": [
            {"aggregate":"SUM","column":{"column_name":"picks_count"},"expressionType":"SIMPLE","label":"Total Picks"},
            {"aggregate":"AVG","column":{"column_name":"picks_per_hour"},"expressionType":"SIMPLE","label":"Picks/h"},
            {"aggregate":"SUM","column":{"column_name":"total_qty_picked"},"expressionType":"SIMPLE","label":"Qtd Total"},
            {"aggregate":"AVG","column":{"column_name":"distinct_skus_picked"},"expressionType":"SIMPLE","label":"SKUs/Turno"},
        ],
        "groupby": ["shift","operator_user","warehouse_id"], "order_desc": True,
        "row_limit": 20, "include_time": False, "time_range": "No filter",
    }),
]:
    s = add_chart(*args)
    if s: chart_ids.append(s)

con.commit()
print(f"\n{len(chart_ids)} charts criados: {chart_ids}")

# ── Dashboard layout ──────────────────────────────────────────────────────────
def build_positions(ids):
    layout = []
    if len(ids) >= 4:  layout.append(("kpi",  ids[0:4]))
    if len(ids) >= 6:  layout.append(("wide", [ids[4], ids[5]]))
    if len(ids) >= 8:  layout.append(("half", [ids[6], ids[7]]))
    if len(ids) >= 10: layout.append(("half", [ids[8], ids[9]]))
    if len(ids) >= 12: layout.append(("half", [ids[10], ids[11]]))
    if len(ids) >= 14: layout.append(("half", [ids[12], ids[13]]))

    pos = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"id":"ROOT_ID","type":"ROOT","children":["GRID_ID"]},
        "GRID_ID": {"id":"GRID_ID","type":"GRID","children":[]},
    }
    row_keys = []
    for ri, (kind, row_ids) in enumerate(layout):
        rk = f"ROW-{ri}"; elems = []
        if kind == "kpi":
            for cid in row_ids:
                ek = f"CHART-{cid}"
                pos[ek] = {"id":ek,"type":"CHART","children":[],"meta":{"chartId":cid,"height":20,"width":6,"sliceName":f"C{cid}"}}
                elems.append(ek)
        elif kind == "wide":
            for ci, cid in enumerate(row_ids):
                ek = f"CHART-{cid}"; w = 16 if ci==0 else 8
                pos[ek] = {"id":ek,"type":"CHART","children":[],"meta":{"chartId":cid,"height":50,"width":w,"sliceName":f"C{cid}"}}
                elems.append(ek)
        else:
            w = 24 // len(row_ids)
            for cid in row_ids:
                ek = f"CHART-{cid}"
                pos[ek] = {"id":ek,"type":"CHART","children":[],"meta":{"chartId":cid,"height":50,"width":w,"sliceName":f"C{cid}"}}
                elems.append(ek)
        pos[rk] = {"id":rk,"type":"ROW","children":elems,"meta":{"background":"BACKGROUND_TRANSPARENT"}}
        row_keys.append(rk)

    pos["GRID_ID"]["children"] = row_keys
    return pos

positions = build_positions(chart_ids)

cur.execute(
    "INSERT INTO dashboards (dashboard_title, slug, position_json, published, created_by_fk, changed_by_fk, created_on, changed_on) VALUES (?,?,?,?,1,1,datetime('now'),datetime('now'))",
    ("WMS Operations", "wms-operations", json.dumps(positions), 1)
)
dash_id = cur.lastrowid

for cid in chart_ids:
    cur.execute("INSERT INTO dashboard_slices (dashboard_id, slice_id) VALUES (?,?)", (dash_id, cid))

con.commit()
con.close()

print(f"\nDashboard 'WMS Operations' criado (id={dash_id})")
print(f"{len(chart_ids)} charts associados")
print(f"URL: http://localhost:8088/superset/dashboard/{dash_id}/")
