from dotenv import load_dotenv
import os
import oracledb

load_dotenv(".env.extract.prod")

dsn = oracledb.makedsn(
    os.environ["ORACLE_HOST"],
    int(os.environ["ORACLE_PORT"]),
    service_name=os.environ["ORACLE_SERVICE_NAME"]
)

query = """
SELECT
    MIN(TRUNC(DATAMOVIMENTO)) AS data_min,
    MAX(TRUNC(DATAMOVIMENTO)) AS data_max,
    COUNT(*) AS total_registros
FROM WMAS.MOVIMENTOPRODUTODIA
WHERE DATAMOVIMENTO IS NOT NULL
"""

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        row = cur.fetchone()

print("\nRESULTADO MOVIMENTAÇÃO")
print("-" * 50)
print(f"Data mínima: {row[0]}")
print(f"Data máxima: {row[1]}")
print(f"Total registros: {row[2]}")
