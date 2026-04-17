from dotenv import load_dotenv
import csv
import os
import oracledb


def to_float(value):
    if value is None:
        return 0.0

    s = str(value).strip()

    if not s:
        return 0.0

    try:
        return float(s)
    except Exception:
        return 0.0


load_dotenv(".env.extract.prod")

dsn = oracledb.makedsn(
    os.environ["ORACLE_HOST"],
    int(os.environ["ORACLE_PORT"]),
    sid=os.environ["ORACLE_SID"]
)

print("Conectando ao Oracle...")

with oracledb.connect(
    user=os.environ["ORACLE_USER"],
    password=os.environ["ORACLE_PASSWORD"],
    dsn=dsn
) as conn:
    with conn.cursor() as cur:
        print("Executando query de pedidos...")

        cur.execute("""
            SELECT
                IDPEDIDO,
                NRPEDIDO,
                CDPRODUTO,
                DSPRODUTO,
                NRQTD,
                VLPRODUTO,
                VALORTOTALLIQUIDO
            FROM WMAS.ESTBPEDIDOITEMDET
            WHERE ROWNUM <= 5000
        """)

        rows = cur.fetchall()

print(f"Linhas carregadas: {len(rows)}")

faturamento_total = 0.0
resumo_produto = {}
resumo_pedido = {}
registros_validos = 0

for (
    idpedido,
    nrpedido,
    cdproduto,
    dsproduto,
    nrqtd,
    vlproduto,
    valortotalliquido
) in rows:

    qtd = to_float(nrqtd)
    vl_unit = to_float(vlproduto)
    vl_total = to_float(valortotalliquido)

    # prioridade: valor total líquido
    if vl_total > 0:
        faturamento = vl_total
    elif qtd > 0 and vl_unit > 0:
        faturamento = qtd * vl_unit
    else:
        faturamento = 0.0

    faturamento_total += faturamento
    registros_validos += 1

    # debug inicial
    if registros_validos <= 10:
        print(f"[DEBUG] qtd={qtd} vl_unit={vl_unit} fat={faturamento}")

    chave_prod = cdproduto or "SEM_PRODUTO"
    if chave_prod not in resumo_produto:
        resumo_produto[chave_prod] = {
            "cdproduto": cdproduto,
            "dsproduto": dsproduto,
            "qtd_total": 0.0,
            "faturamento_total": 0.0,
        }

    resumo_produto[chave_prod]["qtd_total"] += qtd
    resumo_produto[chave_prod]["faturamento_total"] += faturamento

    chave_pedido = nrpedido or str(idpedido) or "SEM_PEDIDO"
    if chave_pedido not in resumo_pedido:
        resumo_pedido[chave_pedido] = {
            "pedido": chave_pedido,
            "faturamento_total": 0.0,
            "itens": 0,
        }

    resumo_pedido[chave_pedido]["faturamento_total"] += faturamento
    resumo_pedido[chave_pedido]["itens"] += 1

print("\nRESULTADO GERAL")
print("-" * 60)
print(f"Registros válidos: {registros_validos}")
print(f"Faturamento estimado total: R$ {faturamento_total:,.2f}")

top_produtos = sorted(
    resumo_produto.values(),
    key=lambda x: x["faturamento_total"],
    reverse=True
)[:10]

top_pedidos = sorted(
    resumo_pedido.values(),
    key=lambda x: x["faturamento_total"],
    reverse=True
)[:10]

print("\nTOP 10 PRODUTOS POR FATURAMENTO")
print("-" * 60)
for p in top_produtos:
    print(
        f"{p['cdproduto']} | {p['dsproduto']} | "
        f"qtd={p['qtd_total']:.2f} | fat=R$ {p['faturamento_total']:,.2f}"
    )

print("\nTOP 10 PEDIDOS POR FATURAMENTO")
print("-" * 60)
for p in top_pedidos:
    print(
        f"pedido={p['pedido']} | itens={p['itens']} | fat=R$ {p['faturamento_total']:,.2f}"
    )

os.makedirs("artifacts/fat", exist_ok=True)

with open("artifacts/fat/top_produtos_faturamento.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["cdproduto", "dsproduto", "qtd_total", "faturamento_total"])
    for p in sorted(resumo_produto.values(), key=lambda x: x["faturamento_total"], reverse=True):
        writer.writerow([
            p["cdproduto"],
            p["dsproduto"],
            f"{p['qtd_total']:.2f}",
            f"{p['faturamento_total']:.2f}",
        ])

with open("artifacts/fat/top_pedidos_faturamento.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["pedido", "itens", "faturamento_total"])
    for p in sorted(resumo_pedido.values(), key=lambda x: x["faturamento_total"], reverse=True):
        writer.writerow([
            p["pedido"],
            p["itens"],
            f"{p['faturamento_total']:.2f}",
        ])

print("\nArquivos gerados:")
print("- artifacts/fat/top_produtos_faturamento.csv")
print("- artifacts/fat/top_pedidos_faturamento.csv")
