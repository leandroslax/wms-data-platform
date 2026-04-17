from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pipelines.extraction.oracle_connector import OracleConnector


IMPORTANT_TABLES = [
    "DOCUMENTO",
    "DOCUMENTODETALHE",
    "ROMANEIO",
    "RESERVA",
    "DEMANDA",
    "DEMANDAITEM",
    "INVENTARIO",
    "CARGAESTOQUE",
    "MOVIMENTOESTOQUE",
    "PRODUTO",
    "VOLUME",
]


def main():
    load_dotenv(".env.extract.prod")

    connector = OracleConnector()

    print("\n[1] Listando tabelas do schema ORAINT...\n")

    tables_sql = """
    SELECT owner, table_name
    FROM all_tables
    WHERE owner = 'ORAINT'
    ORDER BY table_name
    """

    tables = connector.execute_query(tables_sql)

    for t in tables:
        print(f"- {t['table_name']}")

    print("\n[2] Mapeando tabelas importantes...\n")

    found = []
    missing = []

    table_names = {t["table_name"] for t in tables}

    for name in IMPORTANT_TABLES:
        if name in table_names:
            print(f"[OK] {name}")
            found.append(name)
        else:
            print(f"[MISS] {name}")
            missing.append(name)

    print("\n[3] Extraindo colunas...\n")

    columns_by_table = {}

    for table in found:
        print(f"\n>>> {table}")

        sql = f"""
        SELECT column_id, column_name, data_type, data_length
        FROM all_tab_columns
        WHERE owner = 'ORAINT'
          AND table_name = '{table}'
        ORDER BY column_id
        """

        cols = connector.execute_query(sql)
        columns_by_table[table] = cols

        for c in cols:
            print(f"{c['column_id']:>3} | {c['column_name']:<30} | {c['data_type']}")

    output = {
        "schema": "ORAINT",
        "tables_found": len(tables),
        "important_tables_found": found,
        "important_tables_missing": missing,
        "columns": columns_by_table,
    }

    Path("artifacts").mkdir(exist_ok=True)

    with open("artifacts/discovery_oraint.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n✔ arquivo salvo em artifacts/discovery_oraint.json")


if __name__ == "__main__":
    main()
