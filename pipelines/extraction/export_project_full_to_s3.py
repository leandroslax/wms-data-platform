from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import boto3
import oracledb
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv


@dataclass
class ExportSpec:
    entity: str
    source_system: str
    source_table: str
    mode: str
    sql: str
    watermark_column: Optional[str] = None


EXPORT_SPECS: List[ExportSpec] = [
    ExportSpec(
        entity="orders_documento",
        source_system="oracle_oraint",
        source_table="ORAINT.DOCUMENTO",
        mode="watermark",
        watermark_column="DATAEMISSAO",
        sql="""
            SELECT *
            FROM ORAINT.DOCUMENTO
            WHERE DATAEMISSAO >= :start_date
            ORDER BY DATAEMISSAO, SEQUENCIADOCUMENTO
        """.strip(),
    ),
    ExportSpec(
        entity="orders_documentodetalhe",
        source_system="oracle_oraint",
        source_table="ORAINT.DOCUMENTODETALHE",
        mode="watermark",
        watermark_column="DOCUMENTO_DATAEMISSAO",
        sql="""
            SELECT
                d.*,
                h.DATAEMISSAO AS DOCUMENTO_DATAEMISSAO
            FROM ORAINT.DOCUMENTODETALHE d
            JOIN ORAINT.DOCUMENTO h
              ON d.SEQUENCIAINTEGRACAO = h.SEQUENCIAINTEGRACAO
             AND d.SEQUENCIADOCUMENTO = h.SEQUENCIADOCUMENTO
            WHERE h.DATAEMISSAO >= :start_date
        """.strip(),
    ),
    ExportSpec(
        entity="products_snapshot",
        source_system="oracle_oraint",
        source_table="ORAINT.PRODUTO",
        mode="snapshot_full",
        sql="SELECT * FROM ORAINT.PRODUTO",
    ),
    ExportSpec(
        entity="inventory_produtoestoque",
        source_system="oracle_wmas",
        source_table="WMAS.PRODUTOESTOQUE",
        mode="snapshot_full",
        sql="SELECT * FROM WMAS.PRODUTOESTOQUE",
    ),
    ExportSpec(
        entity="movements_entrada_saida",
        source_system="oracle_wmas",
        source_table="WMAS.MOVIMENTOENTRADASAIDA",
        mode="watermark",
        watermark_column="DATAMOVIMENTO",
        sql="""
            SELECT *
            FROM WMAS.MOVIMENTOENTRADASAIDA
            WHERE DATAMOVIMENTO >= :start_date
            ORDER BY DATAMOVIMENTO, SEQUENCIAMOVIMENTO
        """.strip(),
    ),
]


def normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, dt_time.min)
    return value


def normalize_row(columns: List[str], row: Iterable[Any]) -> Dict[str, Any]:
    return {columns[idx]: normalize_value(value) for idx, value in enumerate(row)}


def build_connection():
    dsn = oracledb.makedsn(
        os.environ["ORACLE_HOST"],
        int(os.environ["ORACLE_PORT"]),
        service_name=os.environ["ORACLE_SERVICE_NAME"]
    )
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=dsn
    )


def upload_to_s3(local_path: Path, bucket: str, key: str):
    boto3.client("s3").upload_file(str(local_path), bucket, key)


def export_and_upload(spec, mode, days, bucket, batch_size, extract_date, run_ts):
    params = {}

    if spec.mode == "watermark":
        params["start_date"] = datetime.now() - timedelta(days=days)

    print(f"\n[START] {spec.entity}")

    temp_dir = Path(tempfile.mkdtemp())
    local_parquet = temp_dir / f"{spec.entity}.parquet"

    total_rows = 0
    writer = None
    schema = None

    with build_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(spec.sql, params)
            columns = [c[0] for c in cur.description]

            while True:
                batch = cur.fetchmany(batch_size)
                if not batch:
                    break

                rows = [normalize_row(columns, r) for r in batch]

                if writer is None:
                    table = pa.Table.from_pylist(rows)
                    schema = table.schema
                    writer = pq.ParquetWriter(str(local_parquet), schema, compression="snappy")
                else:
                    table = pa.Table.from_pylist(rows, schema=schema)

                writer.write_table(table)
                total_rows += len(rows)

                print(f"lote -> {len(rows)} | total={total_rows}")

    if writer:
        writer.close()

    if total_rows == 0:
        print("sem dados")
        return

    s3_key = f"{spec.entity}/extraction_date={extract_date}/run_id={run_ts}/{spec.entity}.parquet"

    print("upload S3...")
    upload_to_s3(local_parquet, bucket, s3_key)

    print(f"[END] {spec.entity} -> {total_rows}")


def main():
    load_dotenv(".env.extract.prod")

    bucket = os.environ["S3_BRONZE_BUCKET"]
    now = datetime.now(timezone.utc)

    extract_date = now.strftime("%Y-%m-%d")
    run_ts = now.strftime("%Y%m%dT%H%M%SZ")

    for spec in EXPORT_SPECS:
        export_and_upload(
            spec,
            mode="full_90d",
            days=90,
            bucket=bucket,
            batch_size=5000,
            extract_date=extract_date,
            run_ts=run_ts,
        )


if __name__ == "__main__":
    main()
