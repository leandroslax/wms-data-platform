from dotenv import load_dotenv
import os
import oracledb
import csv

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
ORDER BY data_ref
"""

os.makedirs("pipelines/gold", exist_ok=True)

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

with open("pipelines/gold/fato_faturamento.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["data", "documentos", "faturamento"])

    for data_ref, docs, fat in rows:
        writer.writerow([
            str(data_ref),
            docs,
            float(fat or 0)
        ])

print("Arquivo gerado: pipelines/gold/fato_faturamento.csv")
