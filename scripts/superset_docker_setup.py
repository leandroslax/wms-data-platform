#!/usr/bin/env python3
"""
Roda DENTRO do container wms-superset.
Cria charts + dashboard WMS Operations do zero via modelos SQLAlchemy.

docker exec wms-superset python3 /tmp/superset_docker_setup.py
"""
import json
from superset import app, db
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
from superset.connectors.sqla.models import SqlaTable, TableColumn
from sqlalchemy.orm import Session

with app.app_context():
    # ── Limpa estado anterior ────────────────────────────────────────────
    for d in Dashboard.query.all():
        db.session.delete(d)
    for s in Slice.query.all():
        db.session.delete(s)
    db.session.commit()
    print("🗑️  Limpeza feita")

    # ── Datasets (já criados pela API) ────────────────────────────────────
    ds = {t.table_name: t for t in SqlaTable.query.all()}
    print(f"📦 Datasets: {list(ds.keys())}")

    if not ds:
        print("❌ Nenhum dataset encontrado. Rode superset_setup.py primeiro.")
        exit(1)

    # ── Cria charts via modelo Slice ─────────────────────────────────────
    def make_slice(name, viz, table_name, params):
        if table_name not in ds:
            print(f"  ⚠️  Dataset '{table_name}' não encontrado, pulando '{name}'")
            return None
        sl = Slice(
            slice_name=name,
            viz_type=viz,
            datasource_id=ds[table_name].id,
            datasource_type="table",
            params=json.dumps(params),
        )
        db.session.add(sl)
        db.session.flush()   # gera sl.id
        print(f"  ✅ {name} (id={sl.id})")
        return sl

    slices = []

    s = make_slice(
        "Total de Pedidos", "big_number_total", "fct_orders",
        {"metric": {"aggregate": "COUNT", "column": {"column_name": "order_id"},
                    "expressionType": "SIMPLE", "label": "COUNT"},
         "subheader": "pedidos", "y_axis_format": "SMART_NUMBER"},
    )
    if s: slices.append(s)

    s = make_slice(
        "Movimentações por Dia", "echarts_timeseries_line", "fct_movements",
        {"metrics": [{"aggregate": "COUNT", "column": {"column_name": "movement_id"},
                      "expressionType": "SIMPLE", "label": "Movimentações"}],
         "x_axis": "movement_date", "time_grain_sqla": "P1D",
         "row_limit": 500, "y_axis_format": "SMART_NUMBER"},
    )
    if s: slices.append(s)

    s = make_slice(
        "SLA % no Prazo", "big_number_total", "mart_order_sla",
        {"metric": {"expressionType": "SQL",
                    "sqlExpression": "ROUND(100.0*SUM(CASE WHEN sla_met THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1)",
                    "label": "SLA %"},
         "subheader": "% pedidos no prazo", "y_axis_format": ".1f"},
    )
    if s: slices.append(s)

    s = make_slice(
        "Top Operadores", "table", "mart_operator_productivity",
        {"metrics": [
            {"aggregate": "SUM", "column": {"column_name": "total_picks"},
             "expressionType": "SIMPLE", "label": "Total Picks"},
            {"aggregate": "AVG", "column": {"column_name": "picks_per_hour"},
             "expressionType": "SIMPLE", "label": "Picks/h"},
         ],
         "groupby": ["operator_id"], "order_desc": True,
         "row_limit": 20, "include_time": False},
    )
    if s: slices.append(s)

    s = make_slice(
        "Risco de Stockout", "table", "mart_stockout_risk",
        {"metrics": [
            {"aggregate": "AVG", "column": {"column_name": "days_of_stock"},
             "expressionType": "SIMPLE", "label": "Dias Estoque"},
            {"aggregate": "AVG", "column": {"column_name": "stockout_risk_score"},
             "expressionType": "SIMPLE", "label": "Risk Score"},
         ],
         "groupby": ["product_code"], "order_desc": True,
         "row_limit": 20, "include_time": False},
    )
    if s: slices.append(s)

    s = make_slice(
        "Inventory Turnover", "echarts_bar", "mart_inventory_health",
        {"metrics": [{"aggregate": "AVG", "column": {"column_name": "inventory_turnover"},
                      "expressionType": "SIMPLE", "label": "Turnover Médio"}],
         "groupby": ["product_code"], "order_desc": True,
         "row_limit": 20, "y_axis_format": ".2f"},
    )
    if s: slices.append(s)

    db.session.flush()
    ids = [s.id for s in slices]
    print(f"\n📊 Chart IDs: {ids}")

    # ── Monta position_json com IDs reais ─────────────────────────────────
    def build_positions(ids):
        rows_def = []
        # row 0: chart 0 largura total
        rows_def.append([ids[0]])
        # row 1: charts 1+2
        if len(ids) > 2:
            rows_def.append([ids[1], ids[2]])
        elif len(ids) > 1:
            rows_def.append([ids[1]])
        # row 2: charts 3+4
        if len(ids) > 4:
            rows_def.append([ids[3], ids[4]])
        elif len(ids) > 3:
            rows_def.append([ids[3]])
        # row 3: chart 5
        if len(ids) > 5:
            rows_def.append([ids[5]])

        pos = {
            "DASHBOARD_VERSION_KEY": "v2",
            "ROOT_ID": {"id": "ROOT_ID", "type": "ROOT", "children": ["GRID_ID"]},
            "GRID_ID": {"id": "GRID_ID", "type": "GRID", "children": []},
        }
        row_keys = []
        for ri, row_charts in enumerate(rows_def):
            row_key = f"ROW-{ri}"
            w = 24 // len(row_charts)
            chart_keys = []
            for cid in row_charts:
                ck = f"CHART-{cid}"
                chart_name = next((s.slice_name for s in slices if s.id == cid), f"Chart {cid}")
                pos[ck] = {
                    "id": ck, "type": "CHART", "children": [],
                    "meta": {"chartId": cid, "height": 50, "width": w, "sliceName": chart_name},
                }
                chart_keys.append(ck)
            pos[row_key] = {
                "id": row_key, "type": "ROW", "children": chart_keys,
                "meta": {"background": "BACKGROUND_TRANSPARENT"},
            }
            row_keys.append(row_key)
        pos["GRID_ID"]["children"] = row_keys
        return pos

    positions = build_positions(ids)

    # ── Cria dashboard ────────────────────────────────────────────────────
    dash = Dashboard(
        dashboard_title="WMS Operations",
        slug="wms-operations",
        position_json=json.dumps(positions),
        published=True,
    )
    dash.slices = slices
    db.session.add(dash)
    db.session.commit()

    # ── Verifica ──────────────────────────────────────────────────────────
    dash = Dashboard.query.filter_by(slug="wms-operations").first()
    print(f"\n✅ Dashboard '{dash.dashboard_title}' criado (id={dash.id})")
    print(f"   Charts associados: {[s.slice_name for s in dash.slices]}")
    print(f"\n🔗 http://localhost:8088/dashboard/wms-operations/")
