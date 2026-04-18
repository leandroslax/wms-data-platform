"""
discover_oracle.py — Descobre tabelas e colunas disponíveis no Oracle WMS.
Uso: python pipelines/extraction/discover_oracle.py
"""
import os
import oracledb
from dotenv import load_dotenv

load_dotenv(".env")

host     = os.environ["ORACLE_HOST"]
port     = int(os.environ.get("ORACLE_PORT", 1521))
service  = os.environ.get("ORACLE_SERVICE_NAME")
sid      = os.environ.get("ORACLE_SID")
user     = os.environ["ORACLE_USER"]
password = os.environ["ORACLE_PASSWORD"]

dsn = oracledb.makedsn(host, port, service_name=service) if service else oracledb.makedsn(host, port, sid=sid)
conn = oracledb.connect(user=user, password=password, dsn=dsn)
cur = conn.cursor()

print("\n=== SCHEMAS ACESSÍVEIS ===")
cur.execute("SELECT DISTINCT OWNER FROM ALL_TABLES ORDER BY OWNER")
for row in cur.fetchall():
    print(" ", row[0])

print("\n=== TABELAS em ORAINT e WMAS ===")
cur.execute("""
    SELECT OWNER, TABLE_NAME
    FROM ALL_TABLES
    WHERE OWNER IN ('ORAINT','WMAS')
    ORDER BY OWNER, TABLE_NAME
""")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}")

# Tabelas de interesse para o WMS
targets = [
    ("ORAINT", "MOVIMENTOESTOQUE"),
    ("ORAINT", "PRODUTO"),
    ("ORAINT", "PRODUTOESTOQUE"),
    ("ORAINT", "ESTOQUE"),
    ("ORAINT", "INVENTARIO"),
    ("ORAINT", "CARGAESTOQUE"),
]

for owner, table in targets:
    print(f"\n=== COLUNAS de {owner}.{table} ===")
    try:
        cur.execute("""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM ALL_TAB_COLUMNS
            WHERE OWNER = :o AND TABLE_NAME = :t
            ORDER BY COLUMN_ID
        """, {"o": owner, "t": table})
        rows = cur.fetchall()
        if rows:
            for col, dtype in rows:
                print(f"  {col}  ({dtype})")
        else:
            print("  ⚠️  tabela não encontrada ou sem acesso")
    except Exception as e:
        print(f"  ERRO: {e}")

# Busca tabelas com "estoque" ou "produto" no nome
print("\n=== TABELAS com 'ESTOQUE' ou 'PRODUTO' no nome ===")
cur.execute("""
    SELECT OWNER, TABLE_NAME
    FROM ALL_TABLES
    WHERE (TABLE_NAME LIKE '%ESTOQUE%' OR TABLE_NAME LIKE '%PRODUTO%')
      AND OWNER IN ('ORAINT','WMAS')
    ORDER BY OWNER, TABLE_NAME
""")
for row in cur.fetchall():
    print(f"  {row[0]}.{row[1]}")

cur.close()
conn.close()
print("\n✅ Discovery concluído.")
