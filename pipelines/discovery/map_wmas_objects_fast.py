from __future__ import annotations

import csv
from pathlib import Path
from dotenv import load_dotenv
import os
import oracledb


KEYWORDS = [
    "PED", "PEDIDO", "ORDER", "ORD",
    "ESTO", "ESTOQUE", "INV", "INVENT",
    "MOV", "MOVIM", "TRANS",
    "PROD", "SKU", "ITEM",
    "CLIENT", "VENDA", "NF", "NOTA"
]


def score_name(name: str) -> int:
    upper = name.upper()
    return sum(10 for k in KEYWORDS if k in upper)


def main():
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
                SELECT
                    o.object_name,
                    o.object_type,
                    COUNT(c.column_name) AS column_count,
                    NVL(t.num_rows, 0) AS num_rows
                FROM all_objects o
                LEFT JOIN all_tab_columns c
                    ON o.owner = c.owner
                   AND o.object_name = c.table_name
                LEFT JOIN all_tables t
                    ON o.owner = t.owner
                   AND o.object_name = t.table_name
                WHERE o.owner = 'WMAS'
                  AND o.object_type IN ('TABLE', 'VIEW')
                GROUP BY o.object_name, o.object_type, t.num_rows
                ORDER BY o.object_name
            """)

            rows = []
            total = 0

            print("Iniciando mapeamento do schema WMAS...")
            print("-" * 120)

            for total, (name, obj_type, col_count, num_rows) in enumerate(cur, start=1):
                score = score_name(name)

                row = {
                    "name": name,
                    "type": obj_type,
                    "columns": int(col_count),
                    "rows": int(num_rows) if num_rows else 0,
                    "score": score
                }
                rows.append(row)

                print(
                    f"[{total:04d}] "
                    f"{name:<40} "
                    f"{obj_type:<5} "
                    f"cols={int(col_count):<4} "
                    f"rows={int(num_rows):<10} "
                    f"score={score}"
                )

    rows.sort(key=lambda x: (-x["score"], -x["rows"], -x["columns"], x["name"]))

    output_dir = Path("artifacts/discovery")
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "top_wmas.csv"
    txt_path = output_dir / "top_wmas.txt"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["name", "type", "columns", "rows", "score"]
        )
        writer.writeheader()
        writer.writerows(rows)

    with txt_path.open("w", encoding="utf-8") as f:
        f.write("TOP TABELAS / VIEWS WMAS\n\n")
        for i, r in enumerate(rows[:100], 1):
            f.write(
                f"{i:02d}. {r['name']} [{r['type']}]\n"
                f"    score={r['score']} rows={r['rows']} cols={r['columns']}\n\n"
            )

    print("-" * 120)
    print(f"Mapeamento concluído. Objetos analisados: {total}")
    print(f"CSV: {csv_path}")
    print(f"TXT: {txt_path}")


if __name__ == "__main__":
    main()
