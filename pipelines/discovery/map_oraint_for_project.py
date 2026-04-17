from dotenv import load_dotenv
import os
import oracledb
from collections import defaultdict

load_dotenv(".env.extract.prod")

GROUPS = {
    "faturamento_documento": ["DOCUMENTO", "DOC"],
    "faturamento_item": ["DETALHE", "ITEM"],
    "produto": ["PRODUTO"],
    "logistica": ["ROMANEIO", "VOLUME", "EMBALAGEM", "RESERVA"],
    "estoque": ["ESTOQUE", "INVENTARIO", "MOVIMENTOESTOQUE"],
    "integracao": ["INTEGRACAO", "ERRO", "MENSAGEM", "FLUXO"],
}

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
ORDER BY object_name
"""

def classify(name: str) -> list[str]:
    upper = name.upper()
    matched = []
    for group, keywords in GROUPS.items():
        if any(k in upper for k in keywords):
            matched.append(group)
    return matched or ["outros"]

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

grouped = defaultdict(list)

for object_name, object_type in rows:
    cats = classify(object_name)
    for cat in cats:
        grouped[cat].append((object_name, object_type))

print("\nMAPEAMENTO ORAINT PARA O PROJETO")
print("=" * 80)

for group in sorted(grouped.keys()):
    print(f"\n[{group.upper()}]")
    for name, obj_type in grouped[group]:
        print(f" - {name} ({obj_type})")
