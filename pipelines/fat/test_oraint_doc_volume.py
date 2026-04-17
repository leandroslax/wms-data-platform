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
    "ORAINT.DOCUMENTO",
    "ORAINT.DOCUMENTODETALHE",
    "ORAINT.MOVIMENTOESTOQUE"
]

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        for tabela in TABELAS:
            cur.execute(f"SELECT COUNT(*) FROM {tabela}")
            total = cur.fetchone()[0]
            print(f"{tabela}: {total}")
