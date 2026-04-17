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
            SELECT column_name, data_type, data_length
            FROM all_tab_columns
            WHERE owner = 'WMAS'
              AND table_name = 'ESTBPEDIDOITEMDET'
            ORDER BY column_id
        """)

        rows = cur.fetchall()

        print("COLUNAS DE WMAS.ESTBPEDIDOITEMDET")
        print("-" * 80)
        for col_name, data_type, data_length in rows:
            print(f"{col_name:<35} {data_type:<20} {data_length}")
