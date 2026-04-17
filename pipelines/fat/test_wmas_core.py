from dotenv import load_dotenv
import os
import oracledb

load_dotenv(".env.extract.prod")

dsn = oracledb.makedsn(
    os.environ["ORACLE_HOST"],
    int(os.environ["ORACLE_PORT"]),
    service_name=os.environ["ORACLE_SERVICE_NAME"]
)

TABELAS = [
    "WMAS.PRODUTOESTOQUE",
    "WMAS.MOVIMENTOPRODUTODIA",
    "WMAS.MOVIMENTOPRODUTOMES"
]

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        for t in TABELAS:
            print("\n" + t)
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                total = cur.fetchone()[0]
                print("TOTAL:", total)
            except Exception as e:
                print("ERRO:", e)
