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

# ─── GEO REFERENCE (warehouses + companies) ─────────────────────────────────
print("  Gerando geo_reference (warehouses + companies)...")

# Static geo data matching ENTITY_CEP_MAP in pipelines/enrichment/enrich_geo.py
# Coordinates are state centroids from IBGE for choropleth visualization.
geo_rows = [
    # Warehouses
    ("warehouse", "WH001", "01310-100", "Av. Paulista",     "Bela Vista",   "São Paulo",        "SP", "São Paulo",          "Sudeste",    "3550308", -23.550520, -46.633309),
    ("warehouse", "WH002", "20040-020", "R. da Assembleia", "Centro",       "Rio de Janeiro",   "RJ", "Rio de Janeiro",     "Sudeste",    "3304557", -22.906847, -43.172897),
    ("warehouse", "WH003", "30130-110", "Av. Afonso Pena",  "Centro",       "Belo Horizonte",   "MG", "Minas Gerais",       "Sudeste",    "3106200", -19.918813, -43.938610),
    ("warehouse", "WH004", "80020-180", "R. XV de Novembro","Centro",       "Curitiba",         "PR", "Paraná",             "Sul",        "4106902", -25.428954, -49.267137),
    ("warehouse", "WH005", "40020-010", "Praça da Sé",      "Centro",       "Salvador",         "BA", "Bahia",              "Nordeste",   "2927408", -12.971600, -38.501000),
    ("warehouse", "WH006", "69005-141", "Av. Djalma Batista","Chapada",     "Manaus",           "AM", "Amazonas",           "Norte",      "1302603",  -3.119027, -60.021731),
    ("warehouse", "WH007", "74003-010", "Av. Goiás",        "Centro",       "Goiânia",          "GO", "Goiás",              "Centro-Oeste","5208707",-16.686891, -49.264895),
    # Companies / depositors
    ("company",   "DEP001", "01310-100", "Av. Paulista",    "Bela Vista",   "São Paulo",        "SP", "São Paulo",          "Sudeste",    "3550308", -23.550520, -46.633309),
    ("company",   "DEP002", "20040-020", "R. da Assembleia","Centro",       "Rio de Janeiro",   "RJ", "Rio de Janeiro",     "Sudeste",    "3304557", -22.906847, -43.172897),
    ("company",   "DEP003", "30130-110", "Av. Afonso Pena", "Centro",       "Belo Horizonte",   "MG", "Minas Gerais",       "Sudeste",    "3106200", -19.918813, -43.938610),
    ("company",   "DEP004", "80020-180", "R. XV de Novembro","Centro",      "Curitiba",         "PR", "Paraná",             "Sul",        "4106902", -25.428954, -49.267137),
    ("company",   "DEP005", "40020-010", "Praça da Sé",     "Centro",       "Salvador",         "BA", "Bahia",              "Nordeste",   "2927408", -12.971600, -38.501000),
]

cur.executemany("""
    INSERT INTO bronze.geo_reference
    (entity_type, entity_id, cep, logradouro, bairro, localidade,
     uf, estado, regiao, ibge_code, latitude, longitude, _enriched_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
    ON CONFLICT (entity_type, entity_id) DO UPDATE SET
        cep=EXCLUDED.cep, logradouro=EXCLUDED.logradouro, bairro=EXCLUDED.bairro,
        localidade=EXCLUDED.localidade, uf=EXCLUDED.uf, estado=EXCLUDED.estado,
        regiao=EXCLUDED.regiao, ibge_code=EXCLUDED.ibge_code,
        latitude=EXCLUDED.latitude, longitude=EXCLUDED.longitude,
        _enriched_at=now()
""", geo_rows)
print(f"  {len(geo_rows)} linhas de geo_reference inseridas.")

# ─── WEATHER DAILY (últimos 90 dias × UFs presentes) ─────────────────────────
print("  Gerando weather_daily (90 dias sintéticos × 5 UFs)...")

from datetime import date as date_cls

END_W   = date_cls(2026, 4, 19)
START_W = END_W - timedelta(days=89)

# UFs presentes nos warehouses/companies acima
ufs_weather = ["SP", "RJ", "MG", "PR", "BA", "AM", "GO"]

# Typical seasonal ranges for Brazil (April = end of rainy season in SE)
uf_climate_base = {
    "SP": {"temp": 22, "precip_dry": 2,  "precip_wet": 12, "wind": 12},
    "RJ": {"temp": 26, "precip_dry": 3,  "precip_wet": 14, "wind": 10},
    "MG": {"temp": 21, "precip_dry": 1,  "precip_wet": 10, "wind": 11},
    "PR": {"temp": 18, "precip_dry": 3,  "precip_wet":  8, "wind": 13},
    "BA": {"temp": 27, "precip_dry": 1,  "precip_wet":  6, "wind":  9},
    "AM": {"temp": 28, "precip_dry": 8,  "precip_wet": 20, "wind":  8},
    "GO": {"temp": 24, "precip_dry": 1,  "precip_wet":  9, "wind": 12},
}

# WMO codes for synthetic labeling
wmo_labels = {
    0: "Céu limpo", 1: "Predominantemente limpo", 2: "Parcialmente nublado",
    3: "Nublado", 61: "Chuva fraca", 63: "Chuva moderada", 65: "Chuva forte",
    80: "Pancadas fracas", 81: "Pancadas moderadas",
}

weather_rows = []
d = START_W
while d <= END_W:
    for uf in ufs_weather:
        base   = uf_climate_base.get(uf, {"temp": 22, "precip_dry": 2, "precip_wet": 8, "wind": 10})
        t_mean = round(base["temp"] + random.gauss(0, 2), 1)
        t_min  = round(t_mean - random.uniform(3, 6), 1)
        t_max  = round(t_mean + random.uniform(3, 6), 1)

        # More rain in April (end of rainy season) for SE / CO
        is_rainy = random.random() < (0.55 if uf in ["SP", "RJ", "MG", "AM", "GO"] else 0.25)
        precip = round(random.uniform(base["precip_wet"] * 0.5, base["precip_wet"] * 2.0), 1) if is_rainy else round(random.uniform(0, base["precip_dry"]), 1)
        wind   = round(abs(random.gauss(base["wind"], 3)), 1)

        if precip > 10:
            code = random.choice([63, 65, 80, 81])
        elif precip > 3:
            code = random.choice([61, 80])
        elif precip > 0:
            code = random.choice([1, 2, 61])
        else:
            code = random.choice([0, 1, 2, 3])

        weather_rows.append((
            uf, d,
            t_mean, t_min, t_max,
            precip,
            wmo_labels[code],
            wind,
        ))
    d += timedelta(days=1)

cur.executemany("""
    INSERT INTO bronze.weather_daily
    (location_uf, weather_date,
     avg_temperature_c, min_temperature_c, max_temperature_c,
     precipitation_mm, weather_condition, wind_speed_kmh, _enriched_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s, now())
    ON CONFLICT (location_uf, weather_date) DO UPDATE SET
        avg_temperature_c=EXCLUDED.avg_temperature_c,
        min_temperature_c=EXCLUDED.min_temperature_c,
        max_temperature_c=EXCLUDED.max_temperature_c,
        precipitation_mm=EXCLUDED.precipitation_mm,
        weather_condition=EXCLUDED.weather_condition,
        wind_speed_kmh=EXCLUDED.wind_speed_kmh,
        _enriched_at=now()
""", weather_rows)
print(f"  {len(weather_rows)} registros de weather_daily inseridos ({len(ufs_weather)} UFs × 90 dias).")

cur.close()
conn.close()

print(f"""
✅  Seed 1 ANO completo:
    Pedidos      : {len(orders):>8,}
    Inventário   : {len(inventories):>8,}
    Movimentos   : aprox {mov_seq-1:>7,}
    Produtos     : {len(products):>8,}
    Operadores   : {len(operators):>8,}
    Geo (entid.) : {len(geo_rows):>8,}
    Weather (d.) : {len(weather_rows):>8,}

Próximo passo: airflow trigger dag_transform_dbt
""")
