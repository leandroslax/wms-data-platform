"""
Validação local dos 8 marts dbt com DuckDB.
Substitui unix_timestamp() por epoch() e adapta funções Spark → DuckDB.
Não requer conexão AWS. Usa dados de amostra gerados inline.
"""

import duckdb
from datetime import datetime, timedelta
import random

con = duckdb.connect(":memory:")

# ─────────────────────────────────────────────
# 1. SEED DATA
# ─────────────────────────────────────────────

print("=" * 60)
print("Criando tabelas base com dados de amostra...")
print("=" * 60)

now = datetime(2026, 4, 1, 10, 0, 0)

# fct_orders
orders = []
for i in range(1, 51):
    issued  = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 12))
    # 70% entregue, 30% pendente
    if random.random() < 0.7:
        hours   = random.choice([12, 20, 36, 50, 70, 90])
        delivered = issued + timedelta(hours=hours)
    else:
        delivered = None
    orders.append((
        f"ORD-{i:04d}",
        f"DOC-{i:04d}",
        random.choice(["NF", "OS"]),
        f"COMP-{random.randint(1,3):02d}",
        f"DEP-{random.randint(1,3):02d}",
        issued,
        delivered,
        round(random.uniform(100, 5000), 2),
    ))

con.execute("""
    CREATE TABLE fct_orders AS
    SELECT
        col0  AS order_id,
        col1  AS document_number,
        col2  AS document_type,
        col3  AS company_id,
        col4  AS depositor_id,
        col5  AS issued_at,
        col6  AS delivered_at,
        col7  AS total_value
    FROM (VALUES """ +
    ",".join(
        f"('{r[0]}','{r[1]}','{r[2]}','{r[3]}','{r[4]}',"
        f"TIMESTAMPTZ '{r[5]}',"
        + (f"TIMESTAMPTZ '{r[6]}'" if r[6] else "NULL") +
        f",{r[7]})"
        for r in orders
    ) +
    ")"
)

# fct_inventory_snapshot
inventories = []
for i in range(1, 31):
    avg_cons = random.uniform(0, 20)
    min_stock = random.uniform(0, 100)
    inventories.append((
        f"INV-{i:04d}",
        f"SKU-{random.randint(1,10):03d}",
        f"WH-{random.randint(1,3):02d}",
        f"COMP-{random.randint(1,3):02d}",
        random.choice(["A", "B", "C"]),
        round(min_stock, 1),
        round(min_stock * 1.5, 1),
        round(min_stock * 2.0, 1),
        round(min_stock * 0.3, 1),
        round(min_stock * 0.5, 1),
        round(avg_cons, 2),
    ))

con.execute("""
    CREATE TABLE fct_inventory_snapshot AS
    SELECT
        col0  AS inventory_id,
        col1  AS product_id,
        col2  AS warehouse_id,
        col3  AS company_id,
        col4  AS product_class,
        col5  AS min_stock_qty,
        col6  AS max_stock_qty,
        col7  AS ideal_stock_qty,
        col8  AS safety_stock_qty,
        col9  AS reorder_point,
        col10 AS avg_consumption
    FROM (VALUES """ +
    ",".join(
        f"('{r[0]}','{r[1]}','{r[2]}','{r[3]}','{r[4]}',"
        f"{r[5]},{r[6]},{r[7]},{r[8]},{r[9]},{r[10]})"
        for r in inventories
    ) +
    ")"
)

# fct_movements
movements = []
for i in range(1, 101):
    mov_date = now - timedelta(
        days=random.randint(0, 14),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    qty = random.choice([-10, -5, -3, -1, 1, 3, 5, 10]) * random.randint(1, 5)
    movements.append((
        f"MOV-{i:05d}",
        f"SKU-{random.randint(1,10):03d}",
        f"WH-{random.randint(1,3):02d}",
        f"COMP-{random.randint(1,3):02d}",
        f"OP-{random.randint(1,5):02d}" if random.random() > 0.05 else None,
        qty,
        mov_date,
    ))

con.execute("""
    CREATE TABLE fct_movements AS
    SELECT
        col0 AS movement_id,
        col1 AS product_id,
        col2 AS warehouse_id,
        col3 AS company_id,
        col4 AS operator_user,
        col5 AS qty_delta,
        col6 AS movement_date
    FROM (VALUES """ +
    ",".join(
        f"('{r[0]}','{r[1]}','{r[2]}','{r[3]}',"
        + (f"'{r[4]}'" if r[4] else "NULL") +
        f",{r[5]},TIMESTAMPTZ '{r[6]}')"
        for r in movements
    ) +
    ")"
)

print(f"  fct_orders:             {con.execute('SELECT count(*) FROM fct_orders').fetchone()[0]} rows")
print(f"  fct_inventory_snapshot: {con.execute('SELECT count(*) FROM fct_inventory_snapshot').fetchone()[0]} rows")
print(f"  fct_movements:          {con.execute('SELECT count(*) FROM fct_movements').fetchone()[0]} rows")

# ─────────────────────────────────────────────
# 2. MART QUERIES (adaptadas para DuckDB)
#    Diferença principal: unix_timestamp(x) → epoch(x)
# ─────────────────────────────────────────────

marts = {}

# mart_order_sla
marts["mart_order_sla"] = """
WITH base AS (
    SELECT
        order_id, document_number, document_type,
        company_id, depositor_id, issued_at, delivered_at, total_value,
        CASE
            WHEN delivered_at IS NOT NULL AND issued_at IS NOT NULL
            THEN (epoch(delivered_at) - epoch(issued_at)) / 3600.0
            ELSE NULL
        END AS cycle_time_hours
    FROM fct_orders
    WHERE issued_at IS NOT NULL
),
classified AS (
    SELECT
        *,
        48                                  AS sla_target_hours,
        date_trunc('day',   issued_at)      AS issued_date,
        date_trunc('month', issued_at)      AS issued_month,
        CASE
            WHEN cycle_time_hours IS NULL THEN 'pending'
            WHEN cycle_time_hours <= 24   THEN 'on_time_express'
            WHEN cycle_time_hours <= 48   THEN 'on_time'
            WHEN cycle_time_hours <= 72   THEN 'at_risk'
            ELSE                               'late'
        END AS sla_status
    FROM base
)
SELECT * FROM classified
"""

# mart_inventory_health
marts["mart_inventory_health"] = """
WITH base AS (
    SELECT
        inventory_id, product_id, warehouse_id, company_id, product_class,
        min_stock_qty, max_stock_qty, ideal_stock_qty,
        safety_stock_qty, reorder_point, avg_consumption
    FROM fct_inventory_snapshot
),
enriched AS (
    SELECT
        *,
        CASE WHEN avg_consumption > 0
             THEN round(min_stock_qty / avg_consumption, 1)
             ELSE NULL END AS coverage_days,
        CASE WHEN ideal_stock_qty > 0
             THEN round(min_stock_qty / ideal_stock_qty, 2)
             ELSE NULL END AS stock_utilization_rate,
        CASE
            WHEN avg_consumption > 0 AND min_stock_qty / avg_consumption <= 3  THEN 'critical'
            WHEN avg_consumption > 0 AND min_stock_qty / avg_consumption <= 7  THEN 'high'
            WHEN avg_consumption > 0 AND min_stock_qty / avg_consumption <= 14 THEN 'medium'
            WHEN avg_consumption > 0                                            THEN 'healthy'
            ELSE 'unknown'
        END AS stockout_risk,
        CASE WHEN min_stock_qty <= safety_stock_qty THEN TRUE ELSE FALSE END AS below_safety_stock,
        CASE WHEN min_stock_qty <= reorder_point    THEN TRUE ELSE FALSE END AS below_reorder_point
    FROM base
)
SELECT * FROM enriched
"""

# mart_stockout_risk
marts["mart_stockout_risk"] = """
WITH base AS (
    SELECT
        inventory_id, product_id, warehouse_id, company_id, product_class,
        min_stock_qty        AS current_stock,
        safety_stock_qty,
        reorder_point,
        avg_consumption      AS avg_daily_consumption,
        CASE WHEN avg_consumption > 0
             THEN round(min_stock_qty / avg_consumption, 1)
             ELSE NULL END AS days_to_stockout
    FROM fct_inventory_snapshot
),
classified AS (
    SELECT
        *,
        CASE
            WHEN days_to_stockout IS NULL THEN 'unknown'
            WHEN days_to_stockout <= 0   THEN 'stockout'
            WHEN days_to_stockout <= 3   THEN 'critical'
            WHEN days_to_stockout <= 7   THEN 'high'
            WHEN days_to_stockout <= 14  THEN 'medium'
            ELSE                              'low'
        END AS risk_level,
        current_date AS snapshot_date
    FROM base
)
SELECT * FROM classified
"""

# mart_operator_productivity
marts["mart_operator_productivity"] = """
WITH daily_ops AS (
    SELECT
        operator_user,
        warehouse_id,
        date_trunc('day', movement_date)          AS period_date,
        count(*)                                   AS movement_count,
        sum(abs(qty_delta))                        AS total_qty_handled,
        count(CASE WHEN qty_delta < 0 THEN 1 END) AS outbound_count,
        count(CASE WHEN qty_delta > 0 THEN 1 END) AS inbound_count,
        count(DISTINCT product_id)                 AS distinct_skus
    FROM fct_movements
    WHERE operator_user IS NOT NULL
      AND movement_date  IS NOT NULL
    GROUP BY 1, 2, 3
),
with_scores AS (
    SELECT
        *,
        round(
            (outbound_count * 1.5 + inbound_count) / nullif(movement_count, 0),
            3
        ) AS complexity_index,
        round(total_qty_handled / nullif(movement_count, 0), 2) AS avg_qty_per_move,
        rank() OVER (
            PARTITION BY warehouse_id, period_date
            ORDER BY movement_count DESC
        ) AS daily_ranking
    FROM daily_ops
)
SELECT * FROM with_scores
"""

# mart_picking_performance
marts["mart_picking_performance"] = """
WITH picking_events AS (
    SELECT
        operator_user,
        warehouse_id,
        product_id,
        abs(qty_delta)                    AS qty_picked,
        movement_date,
        date_trunc('day', movement_date)  AS shift_date,
        CASE
            WHEN hour(movement_date) BETWEEN 6  AND 13 THEN 'morning'
            WHEN hour(movement_date) BETWEEN 14 AND 21 THEN 'afternoon'
            ELSE                                            'night'
        END AS shift
    FROM fct_movements
    WHERE qty_delta < 0
      AND operator_user  IS NOT NULL
      AND movement_date  IS NOT NULL
),
aggregated AS (
    SELECT
        operator_user, warehouse_id, shift_date, shift,
        count(*)                   AS picks_count,
        sum(qty_picked)            AS total_qty_picked,
        count(DISTINCT product_id) AS distinct_skus_picked,
        min(movement_date)         AS shift_start,
        max(movement_date)         AS shift_end
    FROM picking_events
    GROUP BY 1, 2, 3, 4
),
with_rates AS (
    SELECT
        *,
        round((epoch(shift_end) - epoch(shift_start)) / 3600.0, 2) AS active_hours,
        CASE
            WHEN epoch(shift_end) > epoch(shift_start)
            THEN round(
                picks_count / ((epoch(shift_end) - epoch(shift_start)) / 3600.0),
                2
            )
            ELSE NULL
        END AS picks_per_hour
    FROM aggregated
)
SELECT * FROM with_rates
"""

# mart_geo_performance
marts["mart_geo_performance"] = """
WITH sla_base AS (
    SELECT
        company_id,
        depositor_id,
        date_trunc('month', issued_at) AS issued_month,
        count(*)                        AS order_count,
        count(CASE WHEN delivered_at IS NOT NULL THEN 1 END) AS delivered_count,
        sum(total_value)                AS total_value,
        avg(
            CASE WHEN delivered_at IS NOT NULL AND issued_at IS NOT NULL
                 THEN (epoch(delivered_at) - epoch(issued_at)) / 3600.0
            END
        )                               AS avg_cycle_time_hours,
        round(
            count(CASE
                WHEN delivered_at IS NOT NULL
                 AND (epoch(delivered_at) - epoch(issued_at)) / 3600.0 <= 48
                THEN 1
            END) * 100.0 / nullif(count(*), 0),
            2
        )                               AS sla_compliance_pct,
        round(
            count(CASE
                WHEN delivered_at IS NOT NULL
                 AND (epoch(delivered_at) - epoch(issued_at)) / 3600.0 > 48
                THEN 1
            END) * 100.0 / nullif(count(*), 0),
            2
        )                               AS late_delivery_pct
    FROM fct_orders
    WHERE issued_at IS NOT NULL
    GROUP BY 1, 2, 3
)
SELECT * FROM sla_base
"""

# mart_geo_inventory
marts["mart_geo_inventory"] = """
SELECT
    warehouse_id,
    company_id,
    product_class,
    count(DISTINCT product_id)                                             AS product_count,
    sum(min_stock_qty)                                                     AS total_current_stock,
    sum(safety_stock_qty)                                                  AS total_safety_stock,
    sum(ideal_stock_qty)                                                   AS total_ideal_stock,
    round(
        avg(CASE WHEN avg_consumption > 0
            THEN min_stock_qty / avg_consumption END),
        1
    )                                                                      AS avg_coverage_days,
    count(CASE WHEN min_stock_qty <= safety_stock_qty THEN 1 END)         AS stockout_count,
    count(CASE WHEN min_stock_qty <= reorder_point    THEN 1 END)         AS below_reorder_count,
    round(
        count(CASE WHEN min_stock_qty > safety_stock_qty THEN 1 END)
        * 100.0 / nullif(count(*), 0),
        2
    )                                                                      AS stock_health_pct
FROM fct_inventory_snapshot
GROUP BY 1, 2, 3
"""

# mart_weather_impact
marts["mart_weather_impact"] = """
WITH order_delays AS (
    SELECT
        company_id,
        depositor_id,
        date_trunc('day',   issued_at) AS issued_date,
        date_trunc('month', issued_at) AS issued_month,
        count(*)                        AS order_count,
        avg(
            CASE WHEN delivered_at IS NOT NULL AND issued_at IS NOT NULL
                 THEN (epoch(delivered_at) - epoch(issued_at)) / 3600.0
            END
        )                               AS avg_cycle_time_hours,
        count(CASE
            WHEN delivered_at IS NOT NULL
             AND (epoch(delivered_at) - epoch(issued_at)) / 3600.0 > 48
            THEN 1
        END)                            AS delayed_order_count,
        round(
            count(CASE
                WHEN delivered_at IS NOT NULL
                 AND (epoch(delivered_at) - epoch(issued_at)) / 3600.0 > 48
                THEN 1
            END) * 100.0 / nullif(count(*), 0),
            2
        )                               AS delay_rate_pct,
        CAST(NULL AS VARCHAR)           AS weather_condition,
        CAST(NULL AS DOUBLE)            AS avg_temperature_c,
        CAST(NULL AS DOUBLE)            AS precipitation_mm
    FROM fct_orders
    WHERE issued_at IS NOT NULL
    GROUP BY 1, 2, 3, 4
)
SELECT * FROM order_delays
"""

# ─────────────────────────────────────────────
# 3. EXECUTAR E VALIDAR
# ─────────────────────────────────────────────

print()
print("=" * 60)
print("Executando marts...")
print("=" * 60)

all_passed = True
results = {}

for name, sql in marts.items():
    try:
        df = con.execute(sql).df()
        results[name] = df
        row_count   = len(df)
        col_count   = len(df.columns)
        null_pks    = 0

        # Verificar coluna PK principal
        pk_col = {
            "mart_order_sla":           "order_id",
            "mart_inventory_health":    "inventory_id",
            "mart_stockout_risk":       "inventory_id",
            "mart_operator_productivity": "operator_user",
            "mart_picking_performance": "operator_user",
            "mart_geo_performance":     "company_id",
            "mart_geo_inventory":       "warehouse_id",
            "mart_weather_impact":      "company_id",
        }.get(name)

        if pk_col and pk_col in df.columns:
            null_pks = df[pk_col].isna().sum()

        status = "✅ PASS" if row_count > 0 and null_pks == 0 else "⚠️  WARN"
        if row_count == 0:
            all_passed = False
            status = "❌ FAIL"

        print(f"\n{status}  {name}")
        print(f"       rows={row_count}  cols={col_count}  null_pk={null_pks}")
        print(f"       columns: {', '.join(df.columns[:8])}{'...' if len(df.columns) > 8 else ''}")

        # Mostrar amostra de colunas-chave por mart
        if name == "mart_order_sla" and "sla_status" in df.columns:
            dist = df["sla_status"].value_counts().to_dict()
            print(f"       sla_status dist: {dist}")

        if name == "mart_inventory_health" and "stockout_risk" in df.columns:
            dist = df["stockout_risk"].value_counts().to_dict()
            print(f"       stockout_risk dist: {dist}")

        if name == "mart_stockout_risk" and "risk_level" in df.columns:
            dist = df["risk_level"].value_counts().to_dict()
            print(f"       risk_level dist: {dist}")

        if name == "mart_picking_performance" and "shift" in df.columns:
            dist = df["shift"].value_counts().to_dict()
            print(f"       shift dist: {dist}")

    except Exception as e:
        all_passed = False
        print(f"\n❌ FAIL  {name}")
        print(f"       ERROR: {e}")

# ─────────────────────────────────────────────
# 4. RESUMO
# ─────────────────────────────────────────────

print()
print("=" * 60)
if all_passed:
    print("✅  Todos os 8 marts validados com sucesso.")
else:
    print("⚠️   Um ou mais marts falharam — veja detalhes acima.")
print("=" * 60)

con.close()
