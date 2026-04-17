from dotenv import load_dotenv
import os
import oracledb

load_dotenv(".env.extract.prod")

dsn = oracledb.makedsn(
    os.environ["ORACLE_HOST"],
    int(os.environ["ORACLE_PORT"]),
    service_name=os.environ["ORACLE_SERVICE_NAME"]
)

# palavras-chave relevantes pro projeto
KEYWORDS = ["ESTOQUE", "MOV", "PRODUTO", "PEDIDO"]

query = """
SELECT table_name
FROM all_tables
WHERE owner = 'WMAS'
ORDER BY table_name
"""

def is_relevant(name):
    upper = name.upper()
    return any(k in upper for k in KEYWORDS)

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        tables = [r[0] for r in cur.fetchall()]

print("TABELAS CANDIDATAS WMAS")
print("-" * 50)

for t in tables:
    if is_relevant(t):
        print(t)
