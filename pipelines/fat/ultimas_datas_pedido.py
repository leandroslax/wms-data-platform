from dotenv import load_dotenv
import os
import oracledb

load_dotenv(".env.extract.prod")

dsn = oracledb.makedsn(
    os.environ["ORACLE_HOST"],
    int(os.environ["ORACLE_PORT"]),
    sid=os.environ["ORACLE_SID"]
)

query = """
SELECT
    TRUNC(DTCADASTRO) AS data_ref,
    COUNT(*) AS qtd_pedidos
FROM WMAS.ESTBPEDIDODET
WHERE DTCADASTRO IS NOT NULL
GROUP BY TRUNC(DTCADASTRO)
ORDER BY data_ref DESC
FETCH FIRST 15 ROWS ONLY
"""

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

print("ULTIMAS DATAS EM ESTBPEDIDODET")
print("-" * 50)
for data_ref, qtd in rows:
    print(f"{data_ref} -> {qtd}")
