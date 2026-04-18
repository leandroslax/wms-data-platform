"""
diagnose_movements.py — Diagnostica a tabela CARGAESTOQUE para entender
por que movements_entrada_saida retorna 0 linhas.

Uso:
    python pipelines/extraction/diagnose_movements.py
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

print("\n=== CARGAESTOQUE — range completo ===")
cur.execute("""
    SELECT
        COUNT(*)                                     AS total,
        MIN(DATAMOVIMENTO)                           AS min_datamov,
        MAX(DATAMOVIMENTO)                           AS max_datamov,
        MIN(DATAEMISSAO)                             AS min_dataemis,
        MAX(DATAEMISSAO)                             AS max_dataemis,
        SUM(CASE WHEN DATAMOVIMENTO IS NULL THEN 1 ELSE 0 END) AS nulls_datamov,
        MIN(COALESCE(DATAMOVIMENTO, DATAEMISSAO))    AS min_data_ref,
        MAX(COALESCE(DATAMOVIMENTO, DATAEMISSAO))    AS max_data_ref
    FROM ORAINT.CARGAESTOQUE
""")
row = cur.fetchone()
labels = ["total", "min_datamov", "max_datamov", "min_dataemis", "max_dataemis",
          "nulls_datamov", "min_data_ref", "max_data_ref"]
for label, value in zip(labels, row):
    print(f"  {label:<20}: {value}")

print("\n=== CARGAESTOQUE — últimos 365 dias (COALESCE) ===")
cur.execute("""
    SELECT COUNT(*)
    FROM ORAINT.CARGAESTOQUE
    WHERE COALESCE(DATAMOVIMENTO, DATAEMISSAO) >= SYSDATE - 365
""")
print(f"  registros últimos 365 dias: {cur.fetchone()[0]}")

print("\n=== CARGAESTOQUE — últimos 365 dias (só DATAMOVIMENTO) ===")
cur.execute("""
    SELECT COUNT(*)
    FROM ORAINT.CARGAESTOQUE
    WHERE DATAMOVIMENTO >= SYSDATE - 365
""")
print(f"  registros últimos 365 dias (DATAMOVIMENTO): {cur.fetchone()[0]}")

print("\n=== MOVIMENTOESTOQUE — range completo ===")
try:
    cur.execute("""
        SELECT
            COUNT(*),
            MIN(DATAMOVIMENTO),
            MAX(DATAMOVIMENTO)
        FROM ORAINT.MOVIMENTOESTOQUE
    """)
    row = cur.fetchone()
    print(f"  total={row[0]}  min={row[1]}  max={row[2]}")
except Exception as e:
    print(f"  ERRO: {e}")

cur.close()
conn.close()
print("\n✅ Diagnóstico concluído.")
