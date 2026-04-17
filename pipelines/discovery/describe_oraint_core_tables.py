from dotenv import load_dotenv
import os
import oracledb

load_dotenv(".env.extract.prod")

TABLES = [
    "DOCUMENTO",
    "DOCUMENTODETALHE",
    "PRODUTO",
    "PRODUTODETALHE",
    "ROMANEIO",
]

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
        for table in TABLES:
            print("\n" + "=" * 100)
            print(f"ORAINT.{table}")
            print("=" * 100)

            cur.execute("""
                SELECT column_id, column_name, data_type, data_length
                FROM all_tab_columns
                WHERE owner = 'ORAINT'
                  AND table_name = :table
                ORDER BY column_id
            """, {"table": table})

            for row in cur:
                print(f"{row[0]:>3} | {row[1]:<40} | {row[2]:<15} | {row[3]}")
