from dotenv import load_dotenv
import os
import oracledb
from datetime import datetime


def to_float(value):
    if value is None:
        return 0.0
    try:
        return float(str(value).strip())
    except:
        return 0.0


load_dotenv(".env.extract.prod")

dsn = oracledb.makedsn(
    os.environ["ORACLE_HOST"],
    int(os.environ["ORACLE_PORT"]),
    sid=os.environ["ORACLE_SID"]
)

hoje = datetime.now().strftime("%Y-%m-%d")

print(f"Calculando faturamento de hoje: {hoje}")

query = """
SELECT
    i.NRPEDIDO,
    i.CDPRODUTO,
    i.NRQTD,
    i.VLPRODUTO,
    h.DTCADASTRO
FROM WMAS.ESTBPEDIDOITEMDET i
JOIN WMAS.ESTBPEDIDODET h
  ON i.IDPEDIDO = h.IDPEDIDO
WHERE TRUNC(h.DTCADASTRO) = TRUNC(SYSDATE)
"""

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

print(f"Linhas de hoje: {len(rows)}")

faturamento = 0.0

for r in rows:
    qtd = to_float(r[2])
    vl = to_float(r[3])
    faturamento += qtd * vl

print("\nRESULTADO")
print("-" * 40)
print(f"Faturamento de hoje: R$ {faturamento:,.2f}")
