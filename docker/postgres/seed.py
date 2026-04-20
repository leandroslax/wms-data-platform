"""
Seed script — popula bronze no PostgreSQL com 1 ANO de dados realistas.
Simula operações WMS: sazonalidade, padrões de turno, SLA variado.

Uso:
    python docker/postgres/seed.py
    # ou via Makefile:
    make seed
"""

import os
import random
from datetime import datetime, timedelta

import psycopg2

# ─── Conexão ────────────────────────────────────────────────────────────────
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", 5432)),
    dbname=os.getenv("POSTGRES_DB", "wms"),
    user=os.getenv("POSTGRES_USER", "wmsadmin"),
    password=os.getenv("POSTGRES_PASSWORD", "wmsadmin2026"),
)
conn.autocommit = True
cur = conn.cursor()

print("Conectado ao PostgreSQL. Iniciando seed (1 ano de dados)...")

# ─── Limpeza ────────────────────────────────────────────────────────────────
cur.execute("TRUNCATE bronze.orders_documento CASCADE")
cur.execute("TRUNCATE bronze.inventory_produtoestoque CASCADE")
cur.execute("TRUNCATE bronze.movements_entrada_saida CASCADE")
cur.execute("TRUNCATE bronze.products_snapshot CASCADE")
print("  Tabelas bronze limpas.")

# ─── Configuração ───────────────────────────────────────────────────────────
random.seed(42)
END_DATE   = datetime(2026, 4, 20, 23, 59, 0)   # hoje
START_DATE = END_DATE - timedelta(days=365)       # 1 ano atrás

companies  = ["EMP-001", "EMP-002", "EMP-003", "EMP-004", "EMP-005"]
depositors = ["DEP-001", "DEP-002", "DEP-003", "DEP-004"]
warehouses = [1, 2, 3]
doc_types  = ["NF", "OS", "TE", "RE", "NF"]  # NF tem peso duplo (mais comum)
classes    = ["A", "A", "B", "B", "C"]        # A mais frequente

# 50 produtos com distribuição ABC
products = (
    [f"SKU-A{i:02d}" for i in range(1, 16)] +   # 15 produtos A — alta rotatividade
    [f"SKU-B{i:02d}" for i in range(1, 21)] +   # 20 produtos B — média rotatividade
    [f"SKU-C{i:02d}" for i in range(1, 16)]     # 15 produtos C — baixa rotatividade
)
product_class = {p: "A" if "A" in p else ("B" if "B" in p else "C") for p in products}

# 20 operadores com nomes brasileiros realistas
operators = [
    "FELIPE.NASC", "FERNANDA.ANDR", "HELDER.SANTOS", "RENAN.RAMALHO",
    "VIVIANE.CRISTINA", "JULIO.CSR", "EDUARDA.SILVA", "JESSICA.LEME",
    "ANDREZA.DIAS", "VALDIRENE.RODRIGUES", "ALINE.COELHO", "MARIA.JOSEMILDA",
    "LAIS.CONCEICAO", "KAYRA.SABINO", "LEILANA.PAIVA", "DIEGO.RIBEIRO",
    "JOSEFA.LOURENCO", "AMANDA.MARINHO", "ELIZANGELA.OLI", "VITORIA.MELO",
]

# ─── Helpers ────────────────────────────────────────────────────────────────
def rand_dt(start, end):
    delta = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta))

def business_weight(dt):
    """Peso de volume por dia da semana e mês (sazonalidade)."""
    dow = dt.weekday()  # 0=seg, 6=dom
    month = dt.month
    # Fim de semana tem ~30% do volume normal
    day_w = 1.0 if dow < 5 else 0.3
    # Sazonalidade: Q4 (out-dez) é 40% maior, jan/fev/abr pico moderado
    month_w = {1: 0.9, 2: 0.8, 3: 1.0, 4: 1.1, 5: 1.0, 6: 0.9,
               7: 0.8, 8: 0.9, 9: 1.0, 10: 1.2, 11: 1.4, 12: 1.5}.get(month, 1.0)
    return day_w * month_w

# ─── ORDERS (~4 500 pedidos em 1 ano) ───────────────────────────────────────
print("  Gerando pedidos (1 ano)...")
orders = []
order_seq = 1

current = START_DATE
while current <= END_DATE:
    # Volume base: 8-18 pedidos por dia útil, 2-5 no fim de semana
    w = business_weight(current)
    daily_count = max(1, int(random.gauss(13, 3) * w))

    for _ in range(daily_count):
        issued = current.replace(
            hour=random.randint(6, 20),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        )
        if issued > END_DATE:
            continue

        # SLA: 80% entregue, 20% ainda em aberto
        # Distribuição de entrega: express (<12h), on_time (12-24h), late (>sla_hours)
        sla_hours = random.choice([12, 12, 24, 24, 24, 48, 48, 72, 96])
        r = random.random()
        if r < 0.82:    # entregue
            if r < 0.15:                         # express (<12h)
                delivery_h = random.uniform(4, 11.9)
            elif r < 0.70:                        # on_time
                delivery_h = random.uniform(12, sla_hours * 0.95)
            else:                                 # late
                delivery_h = random.uniform(sla_hours * 1.05, sla_hours * 3)
            delivered = issued + timedelta(hours=delivery_h)
            if delivered > END_DATE:
                delivered = None  # ainda em aberto se entrega seria no futuro
        else:
            delivered = None  # pendente

        comp = random.choice(companies)
        dep  = random.choice(depositors)
        val  = round(random.lognormvariate(8.0, 0.8), 2)  # distribuição log-normal realista

        orders.append((
            f"SEQ-{order_seq:06d}",
            f"NF-{order_seq:07d}",
            "1",
            random.choice(doc_types),
            comp, dep,
            issued, delivered,
            val,
            f"INT-{order_seq:06d}",
        ))
        order_seq += 1

    current += timedelta(days=1)

cur.executemany("""
    INSERT INTO bronze.orders_documento
    (sequenciadocumento, numerodocumento, seriedocumento, tipodocumento,
     codigoempresa, codigodepositante, dataemissao, dataentrega,
     valortotaldocumento, sequenciaintegracao)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
""", orders)
print(f"  {len(orders):,} pedidos inseridos.")

# ─── INVENTORY (60 SKUs × 3 armazéns × empresas) ────────────────────────────
print("  Gerando inventário...")
inventories = []
inv_seq = 1
for prod in products:
    for wh in warehouses:
        for comp in companies[:3]:
            cls = product_class[prod]
            # Classe A: alto giro, estoque menor; C: baixo giro, estoque maior
            base = {"A": 500, "B": 200, "C": 80}[cls]
            noise = random.uniform(0.6, 1.4)
            ideal = int(base * noise)
            min_s = int(ideal * 0.3)
            max_s = int(ideal * 2.5)
            safety = int(ideal * 0.15)
            reorder = int(ideal * 0.25)
            avg_cons = round(random.uniform(
                {"A": 15, "B": 5, "C": 1}[cls],
                {"A": 50, "B": 20, "C": 8}[cls]
            ), 2)
            inventories.append((
                f"INV-{inv_seq:05d}", prod, str(wh), comp,
                ideal, min_s, max_s, safety, reorder,
                avg_cons, cls,
            ))
            inv_seq += 1

cur.executemany("""
    INSERT INTO bronze.inventory_produtoestoque
    (sequenciaestoque, codigoproduto, codigoestabelecimento, codigoempresa,
     estoqueideal, estoqueminimo, estoquemaximo, estoqueseguranca,
     pontoreposicao, consumomedio, classeproduto)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
""", inventories)
print(f"  {len(inventories):,} linhas de inventário inseridas.")

# ─── MOVEMENTS (~45 000 movimentos em 1 ano) ─────────────────────────────────
print("  Gerando movimentos (isso pode demorar ~30s)...")
movements = []
mov_seq = 1

# Distribuição de produto por classe (A tem mais movimentos)
product_pool = (
    [p for p in products if "A" in p] * 5 +
    [p for p in products if "B" in p] * 3 +
    [p for p in products if "C" in p] * 1
)

current = START_DATE
while current <= END_DATE:
    w = business_weight(current)
    daily_count = max(1, int(random.gauss(125, 25) * w))

    for _ in range(daily_count):
        qty_before = random.randint(0, 500)
        # Tipo de movimento: saída (negativo) 60%, entrada 40%
        if random.random() < 0.6:
            delta = -random.randint(1, min(qty_before, 80)) if qty_before > 0 else random.randint(1, 50)
        else:
            delta = random.randint(1, 100)
        qty_after = max(0, qty_before + delta)

        mov_dt = current.replace(
            hour=random.randint(6, 22),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        )
        if mov_dt > END_DATE:
            continue

        prod = random.choice(product_pool)
        wh   = random.choice(warehouses)
        dep  = random.choice(depositors)
        op   = random.choice(operators) if random.random() > 0.02 else None

        movements.append((
            f"MOV-{mov_seq:07d}",
            prod, str(wh), dep,
            qty_before, qty_after,
            mov_dt,
            "CONFIRMADO" if random.random() > 0.05 else "PENDENTE",
            op, None,
        ))
        mov_seq += 1

    current += timedelta(days=1)

    # Insert em batches de 5000 para não explodir memória
    if len(movements) >= 5000:
        cur.executemany("""
            INSERT INTO bronze.movements_entrada_saida
            (sequenciamovimento, codigoproduto, codigoestabelecimento, codigodepositante,
             quantidadeanterior, quantidadeatual, datamovimento,
             estadomovimento, usuario, observacao)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, movements)
        mov_seq_done = movements[-1][0]
        print(f"    ... batch inserido até {mov_seq_done} ({mov_seq-1:,} movimentos)")
        movements = []

# Insere restante
if movements:
    cur.executemany("""
        INSERT INTO bronze.movements_entrada_saida
        (sequenciamovimento, codigoproduto, codigoestabelecimento, codigodepositante,
         quantidadeanterior, quantidadeatual, datamovimento,
         estadomovimento, usuario, observacao)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, movements)
print(f"  {mov_seq-1:,} movimentos inseridos no total.")

# ─── PRODUCTS SNAPSHOT ───────────────────────────────────────────────────────
psnap = []
descriptions = {
    "A": ["Componente Eletronico", "Peca de Reposicao", "Insumo Industrial"],
    "B": ["Material de Embalagem", "Produto Quimico", "Ferramenta"],
    "C": ["Item de Escritorio", "Equipamento", "Acessorio"],
}
for prod in products:
    cls = product_class[prod]
    desc = random.choice(descriptions[cls])
    for wh in warehouses:
        psnap.append((
            prod, str(wh),
            f"{desc} {prod}",
            random.choice(["UN", "KG", "CX", "PC"]),
            cls,
        ))

cur.executemany("""
    INSERT INTO bronze.products_snapshot
    (codigoproduto, codigoestabelecimento, descricaoproduto, unidademedida, classeproduto)
    VALUES (%s,%s,%s,%s,%s)
""", psnap)
print(f"  {len(psnap):,} product snapshots inseridos.")

cur.close()
conn.close()

print(f"""
✅  Seed 1 ANO completo:
    Pedidos    : {len(orders):>8,}
    Inventário : {len(inventories):>8,}
    Movimentos : aprox {mov_seq-1:>7,}
    Produtos   : {len(products):>8,}
    Operadores : {len(operators):>8,}

Próximo passo: airflow trigger dag_transform_dbt
""")
