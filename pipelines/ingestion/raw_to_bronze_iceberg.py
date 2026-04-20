"""
raw_to_bronze_iceberg.py
------------------------
Lê Parquet do bucket raw e faz MERGE/UPSERT nas tabelas Iceberg do bronze
via PyIceberg + Glue Catalog.

Uso:
    python raw_to_bronze_iceberg.py --entity orders_documento --run-date 2026-04-18
    python raw_to_bronze_iceberg.py --all --run-date 2026-04-18
"""
from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timezone
from typing import Optional

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.fs as pafs
from dotenv import load_dotenv
from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NoSuchTableError
from pyiceberg.schema import Schema
from pyiceberg.table.upsert_util import _match_columns  # noqa: internal helper

# ── Configuração ───────────────────────────────────────────────────────────────

AWS_REGION      = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID  = os.getenv("AWS_ACCOUNT_ID", "896159010925")
ENVIRONMENT     = os.getenv("ENVIRONMENT", "dev")

RAW_BUCKET      = os.getenv("S3_RAW_BUCKET",    f"wms-dp-{ENVIRONMENT}-raw-{AWS_REGION}-{AWS_ACCOUNT_ID}")
BRONZE_BUCKET   = os.getenv("S3_BRONZE_BUCKET",  f"wms-dp-{ENVIRONMENT}-bronze-{AWS_REGION}-{AWS_ACCOUNT_ID}")
GLUE_DB_BRONZE  = os.getenv("GLUE_DB_BRONZE",    f"wms_bronze_{ENVIRONMENT}")

# Chaves de negócio por entidade — usadas no MERGE
PRIMARY_KEYS: dict[str, list[str]] = {
    "orders_documento":         ["sequenciadocumento"],
    "orders_documentodetalhe":  ["sequenciadocumento", "sequenciaitemdetalhe"],
    "inventory_produtoestoque": ["sequenciaestoque"],
    "movements_entrada_saida":  ["sequenciamovimento"],
    "products_snapshot":        ["codigoproduto", "codigoestabelecimento"],
}


def get_catalog() -> object:
    return load_catalog(
        "glue",
        **{
            "type": "glue",
            "warehouse": f"s3://{BRONZE_BUCKET}/iceberg/",
            "s3.region": AWS_REGION,
        },
    )


def list_raw_files(entity: str, run_date: str) -> list[str]:
    """Lista arquivos Parquet no raw para a entidade/data informada."""
    s3 = boto3.client("s3", region_name=AWS_REGION)
    prefix = f"entity={entity}/date={run_date}/"
    resp = s3.list_objects_v2(Bucket=RAW_BUCKET, Prefix=prefix)
    return [
        f"s3://{RAW_BUCKET}/{obj['Key']}"
        for obj in resp.get("Contents", [])
        if obj["Key"].endswith(".parquet")
    ]


def read_parquet_from_s3(s3_uris: list[str]) -> pa.Table:
    """Lê múltiplos Parquet do S3 e concatena em uma única Arrow Table."""
    s3_fs = pafs.S3FileSystem(region=AWS_REGION)
    tables = []
    for uri in s3_uris:
        path = uri.replace("s3://", "")
        tables.append(pq.read_table(path, filesystem=s3_fs))
    return pa.concat_tables(tables)


def ensure_database(catalog) -> None:
    try:
        catalog.load_namespace_properties(GLUE_DB_BRONZE)
    except Exception:
        catalog.create_namespace(
            GLUE_DB_BRONZE,
            properties={"comment": f"WMS bronze layer — Iceberg ({ENVIRONMENT})"},
        )


def upsert_to_bronze(catalog, entity: str, arrow_table: pa.Table) -> None:
    """Cria ou faz MERGE na tabela Iceberg do bronze."""
    table_name = f"{GLUE_DB_BRONZE}.{entity}"
    pk_cols = PRIMARY_KEYS.get(entity, [])

    try:
        iceberg_table = catalog.load_table(table_name)
        print(f"  tabela existente: {table_name} — fazendo MERGE por {pk_cols}")
        iceberg_table.upsert(arrow_table, join_cols=pk_cols)
    except NoSuchTableError:
        print(f"  tabela nova: {table_name} — criando e inserindo")
        iceberg_table = catalog.create_table(
            table_name,
            schema=arrow_table.schema,
            location=f"s3://{BRONZE_BUCKET}/iceberg/{entity}/",
            properties={
                "write.format.default": "parquet",
                "write.parquet.compression-codec": "snappy",
            },
        )
        iceberg_table.append(arrow_table)

    snap = iceberg_table.current_snapshot()
    print(f"  snapshot_id: {snap.snapshot_id}")
    print(f"  registros no arquivo: {len(arrow_table)}")


def process_entity(entity: str, run_date: str) -> dict:
    print(f"\n[ENTITY] {entity} | date={run_date}")

    files = list_raw_files(entity, run_date)
    if not files:
        print(f"  sem arquivos em raw para {entity}/{run_date}")
        return {"entity": entity, "status": "skipped", "files": 0}

    print(f"  arquivos encontrados: {len(files)}")
    arrow_table = read_parquet_from_s3(files)
    print(f"  linhas lidas: {len(arrow_table)}")

    catalog = get_catalog()
    ensure_database(catalog)
    upsert_to_bronze(catalog, entity, arrow_table)

    return {"entity": entity, "status": "ok", "files": len(files), "rows": len(arrow_table)}


def main():
    load_dotenv(".env.extract.prod")

    parser = argparse.ArgumentParser(description="Raw Parquet → Bronze Iceberg (MERGE)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--entity", help="Entidade específica a processar")
    group.add_argument("--all", action="store_true", help="Processar todas as entidades")
    parser.add_argument(
        "--run-date",
        default=date.today().isoformat(),
        help="Data de extração (YYYY-MM-DD), default=hoje",
    )
    args = parser.parse_args()

    entities = list(PRIMARY_KEYS.keys()) if args.all else [args.entity]
    run_date = args.run_date

    print("=" * 80)
    print("RAW → BRONZE ICEBERG")
    print(f"raw bucket.....: {RAW_BUCKET}")
    print(f"bronze bucket..: {BRONZE_BUCKET}")
    print(f"glue database..: {GLUE_DB_BRONZE}")
    print(f"run date.......: {run_date}")
    print(f"entidades......: {entities}")
    print("=" * 80)

    results = [process_entity(e, run_date) for e in entities]

    print("\n" + "=" * 80)
    print("RESUMO")
    print("-" * 80)
    for r in results:
        print(f"  {r['entity']:<35} status={r['status']}  rows={r.get('rows', '-')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
