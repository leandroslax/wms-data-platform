from dotenv import load_dotenv
import os
import oracledb

load_dotenv(".env.extract.prod")

dsn = oracledb.makedsn(
    os.environ["ORACLE_HOST"],
    int(os.environ["ORACLE_PORT"]),
    sid=os.environ["ORACLE_SID"]
)

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                NRPEDIDO,
                CDPRODUTO,
                DSPRODUTO,
                NRQTD,
                VLPRODUTO,
                VALORTOTALLIQUIDO
            FROM WMAS.ESTBPEDIDOITEMDET
            WHERE ROWNUM <= 30
        """)

        rows = cur.fetchall()

for row in rows:
    print("-" * 100)
    print(f"pedido           : {row[0]!r}")
    print(f"produto          : {row[1]!r}")
    print(f"descricao        : {row[2]!r}")
    print(f"nrqtd            : {row[3]!r}")
    print(f"vlproduto        : {row[4]!r}")
    print(f"valortotalliquido: {row[5]!r}")
