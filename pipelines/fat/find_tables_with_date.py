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
            SELECT table_name, column_name
            FROM all_tab_columns
            WHERE owner = 'WMAS'
              AND (
                   LOWER(column_name) LIKE '%data%'
                OR LOWER(column_name) LIKE '%dt%'
              )
            ORDER BY table_name
        """)

        rows = cur.fetchall()

print("Tabelas com colunas de data:")
print("-" * 60)

for t, c in rows:
    print(f"{t} -> {c}")
