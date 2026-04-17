from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import oracledb
from dotenv import load_dotenv


KEYWORDS = {
    "orders": [
        "PED", "PEDIDO", "ORDER", "ORD", "VENDA", "NF", "NOTA", "FAT", "CLIENT", "ITEM"
    ],
    "inventory": [
        "ESTO", "ESTOQUE", "INV", "INVENT", "SALDO", "PROD", "SKU", "ITEM", "ARMAZ", "LOCAL"
    ],
    "movements": [
        "MOV", "MOVIM", "TRANS", "SAIDA", "ENTRADA", "SEPAR", "EXPED", "RECEB", "ROMAN", "CARGA"
    ],
}


@dataclass
class OracleConfig:
    host: str
    port: int
    sid: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        return oracledb.makedsn(self.host.strip(), self.port, sid=self.sid.strip())


class OracleConnector:
    def __init__(self) -> None:
        self.config = OracleConfig(
            host=os.environ["ORACLE_HOST"].strip(),
            port=int(os.environ.get("ORACLE_PORT", "1521")),
            sid=os.environ["ORACLE_SID"].strip(),
            user=os.environ["ORACLE_USER"].strip(),
            password=os.environ["ORACLE_PASSWORD"],
        )

    def execute(self, sql: str, binds: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with oracledb.connect(
            user=self.config.user,
            password=self.config.password,
            dsn=self.config.dsn,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, binds or {})
                columns = [c[0].lower() for c in cursor.description or []]
                rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def score_object(name: str, columns: list[str]) -> tuple[int, list[str]]:
    upper_name = name.upper()
    upper_cols = [c.upper() for c in columns]
    reasons: list[str] = []
    score = 0

    for domain, words in KEYWORDS.items():
        matched = [w for w in words if w in upper_name]
        if matched:
            points = min(len(matched) * 10, 30)
            score += points
            reasons.append(f"{domain}:nome={','.join(matched[:5])}")

    relevant_columns = [
        "ID", "COD", "DATA", "DT", "STATUS", "QTD", "QUANT", "VALOR",
        "CLIENTE", "PRODUTO", "SKU", "ITEM", "LOCAL", "ARMAZEM"
    ]
    col_matches = [c for c in upper_cols if any(rc in c for rc in relevant_columns)]
    if col_matches:
        bonus = min(len(col_matches) * 2, 20)
        score += bonus
        reasons.append(f"colunas_relevantes={len(col_matches)}")

    if len(columns) >= 10:
        score += 5
        reasons.append("estrutura_media_ou_grande")

    return score, reasons


def get_objects(conn: OracleConnector, owner: str) -> list[dict[str, Any]]:
    sql = """
    SELECT object_name, object_type
    FROM all_objects
    WHERE owner = :owner
      AND object_type IN ('TABLE', 'VIEW')
    ORDER BY object_type, object_name
    """
    return conn.execute(sql, {"owner": owner})


def get_columns(conn: OracleConnector, owner: str, object_name: str) -> list[dict[str, Any]]:
    sql = """
    SELECT column_id, column_name, data_type, data_length
    FROM all_tab_columns
    WHERE owner = :owner
      AND table_name = :object_name
    ORDER BY column_id
    """
    return conn.execute(sql, {"owner": owner, "object_name": object_name})


def main() -> None:
    load_dotenv(".env.extract.prod")

    owner = os.environ.get("DISCOVERY_OWNER", "WMAS").strip().upper()
    output_dir = Path("artifacts/discovery")
    output_dir.mkdir(parents=True, exist_ok=True)

    connector = OracleConnector()
    objects = get_objects(connector, owner)

    ranked_rows: list[dict[str, Any]] = []

    for obj in objects:
        object_name = str(obj["object_name"])
        object_type = str(obj["object_type"])

        columns_meta = get_columns(connector, owner, object_name)
        columns = [str(c["column_name"]) for c in columns_meta]

        score, reasons = score_object(object_name, columns)

        ranked_rows.append(
            {
                "owner": owner,
                "object_name": object_name,
                "object_type": object_type,
                "column_count": len(columns),
                "score": score,
                "reasons": " | ".join(reasons),
                "sample_columns": ", ".join(columns[:15]),
            }
        )

    ranked_rows.sort(
        key=lambda x: (
            -int(x["score"]),
            x["object_name"],
        )
    )

    csv_path = output_dir / "wmas_object_ranking.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "owner",
                "object_name",
                "object_type",
                "column_count",
                "score",
                "reasons",
                "sample_columns",
            ],
        )
        writer.writeheader()
        writer.writerows(ranked_rows)

    top20_path = output_dir / "wmas_top20.txt"
    with top20_path.open("w", encoding="utf-8") as f:
        f.write("TOP 20 OBJETOS CANDIDATOS DO SCHEMA WMAS\n")
        f.write("=" * 60 + "\n\n")
        for i, row in enumerate(ranked_rows[:20], start=1):
            f.write(
                f"{i:02d}. {row['object_name']} [{row['object_type']}]\n"
                f"    score: {row['score']}\n"
                f"    column_count: {row['column_count']}\n"
                f"    reasons: {row['reasons']}\n"
                f"    sample_columns: {row['sample_columns']}\n\n"
            )

    print("Mapeamento concluído com sucesso.")
    print(f"Objetos analisados: {len(ranked_rows)}")
    print(f"CSV gerado em: {csv_path}")
    print(f"Resumo top 20 em: {top20_path}")


if __name__ == "__main__":
    main()
