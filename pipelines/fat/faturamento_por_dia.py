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
    TRUNC(DATAEMISSAO) AS data_ref,
    COUNT(*) AS documentos,
    SUM(VALORTOTALDOCUMENTO) AS faturamento
FROM ORAINT.DOCUMENTO
GROUP BY TRUNC(DATAEMISSAO)
ORDER BY data_ref DESC
FETCH FIRST 10 ROWS ONLY
"""

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

print("\nFATURAMENTO POR DIA")
print("-" * 50)

for data_ref, docs, fat in rows:
    print(f"{data_ref} | docs={docs} | R$ {float(fat or 0):,.2f}")
