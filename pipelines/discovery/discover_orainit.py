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


def main() -> None:
    project_root = Path("/Users/leandrosantos/Downloads/wms-data-platform")
    load_dotenv(project_root / ".env.extract.prod")

    connector = OracleConnector()

    tables_sql = """
    select
        owner,
        table_name
    from all_tables
    where owner = 'ORAINT'
    order by table_name
    """

    columns_sql = f"""
    select
        owner,
        table_name,
        column_id,
        column_name,
        data_type,
        data_length,
        nullable
    from all_tab_columns
    where owner = 'ORAINT'
      and table_name in ({",".join("'" + name + "'" for name in IMPORTANT_TABLES)})
    order by table_name, column_id
    """

    tables = connector.execute_query(tables_sql)
    columns = connector.execute_query(columns_sql)

    discovered_table_names = {row["table_name"] for row in tables}
    important_found = [name for name in IMPORTANT_TABLES if name in discovered_table_names]
    important_missing = [name for name in IMPORTANT_TABLES if name not in discovered_table_names]

    grouped_columns: dict[str, list[dict]] = {}
    for row in columns:
        grouped_columns.setdefault(row["table_name"], []).append(
            {
                "column_id": row["column_id"],
                "column_name": row["column_name"],
                "data_type": row["data_type"],
                "data_length": row["data_length"],
                "nullable": row["nullable"],
            }
        )

    payload = {
        "schema": "ORAINT",
        "important_table_candidates": {
            "orders": ["DOCUMENTO", "DOCUMENTODETALHE", "ROMANEIO", "RESERVA", "DEMANDA", "DEMANDAITEM"],
            "inventory": ["INVENTARIO", "CARGAESTOQUE"],
            "movements": ["MOVIMENTOESTOQUE"],
            "master_data": ["PRODUTO", "VOLUME"],
        },
        "tables_found": tables,
        "important_tables_found": important_found,
        "important_tables_missing": important_missing,
        "columns_by_table": grouped_columns,
    }

    output_path = project_root / "artifacts" / "discovery_orainit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "status": "ok",
        "schema": "ORAINT",
        "tables_found": len(tables),
        "important_tables_found": important_found,
        "important_tables_missing": important_missing,
        "output_file": str(output_path),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
