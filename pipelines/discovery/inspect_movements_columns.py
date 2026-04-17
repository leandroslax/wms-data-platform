from dotenv import load_dotenv
import os
import oracledb

load_dotenv(".env.extract.prod")

dsn = oracledb.makedsn(
    os.environ["ORACLE_HOST"],
    int(os.environ["ORACLE_PORT"]),
    service_name=os.environ["ORACLE_SERVICE_NAME"]
)

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM all_tab_columns
            WHERE owner = 'WMAS'
              AND table_name = 'MOVIMENTOENTRADASAIDA'
        """)

        print("COLUNAS:")
        print("-" * 50)

        for row in cur:
            print(row[0])
