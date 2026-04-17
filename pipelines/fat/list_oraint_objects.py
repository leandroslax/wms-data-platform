from dotenv import load_dotenv
import os
import oracledb

load_dotenv(".env.extract.prod")

dsn = oracledb.makedsn(
    os.environ["ORACLE_HOST"],
    int(os.environ["ORACLE_PORT"]),
    service_name=os.environ["ORACLE_SERVICE_NAME"]
)

query = """
SELECT object_name, object_type
FROM all_objects
WHERE owner = 'ORAINT'
  AND object_type IN ('TABLE', 'VIEW')
ORDER BY object_type, object_name
"""

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

print("OBJETOS DO SCHEMA ORAINT")
print("-" * 80)
print(f"Total: {len(rows)}")
for obj_name, obj_type in rows:
    print(f"{obj_type:<6} {obj_name}")
