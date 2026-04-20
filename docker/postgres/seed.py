"""
Seed script — popula bronze no PostgreSQL local com dados de amostra.
Simula extração do Oracle WMS sem precisar de conexão real.

Uso:
    python docker/postgres/seed.py
    # ou via Makefile:
    make seed
"""

import os
import random
from datetime import datetime, timedelta

import psycopg2

# ─── Conexão ────────────────────────────────────────────────
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", 5432)),
    dbname=os.getenv("POSTGRES_DB", "wms"),
    user=os.getenv("POSTGRES_USER", "wmsadmin"),
    password=os.getenv("POSTGRES_PASSWORD", "wmsadmin2026"),
)
conn.autocommit = True
cur = conn.cursor()

print("Conectado ao PostgreSQL. Iniciando seed...")

# ─── Limpeza ────────────────────────────────────────────────
cur.execute("TRUNCATE bronze.orders_documento CASCADE")
cur.execute("TRUNCATE bronze.inventory_produtoestoque CASCADE")
cur.execute("TRUNCATE bronze.movements_entrada_saida CASCADE")
cur.execute("TRUNCATE bronze.products_snapshot CASCADE")
print("  Tabelas bronze limpas.")

# ─── Helpers ────────────────────────────────────────────────
random.seed(42)
now = datetime(2026, 4, 1, 10, 0, 0)

companies    = ["EMP-01", "EMP-02", "EMP-03"]
depositors   = ["DEP-01", "DEP-02", "DEP-03"]
warehouses   = ["WH-01", "WH-02", "WH-03"]
products     = [f"SKU-{i:03d}" for i in range(1, 21)]
operators    = [f"OP-{i:02d}" for i in range(1, 6)]
doc_types    = ["NF", "OS", "TE"]
classes      = ["A", "B", "C"]

# ─── Orders ─────────────────────────────────────────────────
orders = []
for i in range(1, 201):
    issued = now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 12))
    delivered = (issued + timedelta(hours=random.choice([12, 24, 36, 50, 72, 96]))) \
                if random.random() < 0.75 else None
    orders.append((
        f"SEQ-{i:05d}",
        f"NF-{i:06d}",
        "1",
        random.choice(doc_types),
        random.choice(companies),
        random.choice(depositors),
        issued,
        delivered,
        round(random.uniform(100, 15000), 2),
        f"INT-{i:05d}",
    ))

cur.executemany("""
    INSERT INTO bronze.orders_documento
    (sequenciadocumento, numerodocumento, seriedocumento, tipodocumento,
     codigoempresa, codigodepositante, dataemissao, dataentrega,
     valortotaldocumento, sequenciaintegracao)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
""", orders)
print(f"  {len(orders)} orders inseridos.")

# ─── Inventory ──────────────────────────────────────────────
inventories = []
for i, (prod, wh, comp) in enumerate(
    [(p, w, c) for p in products[:10] for w in warehouses for c in companies[:2]], 1
):
    avg_cons = round(random.uniform(0, 25), 2)
    min_stock = random.randint(0, 150)
    inventories.append((
        f"INV-{i:04d}", prod, wh, comp,
        min_stock * 2, min_stock, min_stock * 3,
        int(min_stock * 0.3), int(min_stock * 0.5),
        avg_cons, random.choice(classes),
    ))

cur.executemany("""
    INSERT INTO bronze.inventory_produtoestoque
    (sequenciaestoque, codigoproduto, codigoestabelecimento, codigoempresa,
     estoqueideal, estoqueminimo, estoquemaximo, estoqueseguranca,
     pontoreposicao, consumomedio, classeproduto)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
""", inventories)
print(f"  {len(inventories)} inventory rows inseridos.")

# ─── Movements ──────────────────────────────────────────────
movements = []
for i in range(1, 501):
    qty_before = random.randint(0, 200)
    delta      = random.choice([-20, -10, -5, -1, 1, 5, 10, 20]) * random.randint(1, 3)
    qty_after  = max(0, qty_before + delta)
    mov_date   = now - timedelta(
        days=random.randint(0, 30),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )
    movements.append((
        f"MOV-{i:05d}",
        random.choice(products),
        random.choice(warehouses),
        random.choice(depositors),
        qty_before, qty_after,
        mov_date,
        random.choice(["CONFIRMADO", "PENDENTE"]),
        random.choice(operators) if random.random() > 0.05 else None,
        None,
    ))

cur.executemany("""
    INSERT INTO bronze.movements_entrada_saida
    (sequenciamovimento, codigoproduto, codigoestabelecimento, codigodepositante,
     quantidadeanterior, quantidadeatual, datamovimento,
     estadomovimento, usuario, observacao)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
""", movements)
print(f"  {len(movements)} movements inseridos.")

# ─── Products snapshot ──────────────────────────────────────
psnap = []
for prod in products:
    for wh in warehouses:
        psnap.append((
            prod, wh,
            f"Produto {prod}",
            "UN",
            random.choice(classes),
        ))

cur.executemany("""
    INSERT INTO bronze.products_snapshot
    (codigoproduto, codigoestabelecimento, descricaoproduto, unidademedida, classeproduto)
    VALUES (%s,%s,%s,%s,%s)
""", psnap)
print(f"  {len(psnap)} product snapshots inseridos.")

cur.close()
conn.close()
print("\n✅  Seed completo. Bronze está pronto para dbt run.")
