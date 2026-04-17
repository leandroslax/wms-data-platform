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
    COUNT(*) AS total_docs,
    SUM(VALORTOTALDOCUMENTO) AS faturamento
FROM ORAINT.DOCUMENTO
WHERE TRUNC(DATAEMISSAO) = TRUNC(SYSDATE)
"""

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        total_docs, faturamento = cur.fetchone()

print("\nFATURAMENTO REAL HOJE")
print("-" * 40)
print(f"Documentos: {total_docs}")
print(f"Faturamento: R$ {float(faturamento or 0):,.2f}")
