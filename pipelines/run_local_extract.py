from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from dotenv import load_dotenv

from pipelines.extraction.checkpoint import write_checkpoint
from pipelines.extraction.oracle_connector import OracleConnector


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def _load_sql(sql_path: Path) -> str:
    return sql_path.read_text(encoding="utf-8").strip()


def _upload_payload(bucket: str, key: str, payload: list[dict]) -> None:
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, default=_json_default).encode("utf-8"),
        ContentType="application/json",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entity", choices=["orders", "inventory", "movements"], required=True)
    parser.add_argument("--env-file", default=".env.extract.prod")
    parser.add_argument("--sql-dir", default="config/sql/prod")
    args = parser.parse_args()

    load_dotenv(args.env_file)

    run_ts = datetime.now(timezone.utc)
    run_id = f"{args.entity}-{run_ts.strftime('%Y%m%dT%H%M%SZ')}"
    extraction_date = run_ts.strftime("%Y-%m-%d")

    sql_path = Path(args.sql_dir) / f"{args.entity}.sql"
    sql = _load_sql(sql_path)

    connector = OracleConnector()
    rows = connector.execute_query(sql)

    source_table_env = f"EXTRACTION_SOURCE_TABLE_{args.entity.upper()}"
    source_table = os.environ.get(source_table_env, "undefined")
    source_system = os.environ.get("EXTRACTION_SOURCE_SYSTEM", "oracle_wms")

    envelope_rows = [
        {
            "entity_name": args.entity,
            "extraction_timestamp": run_ts.isoformat(),
            "source_system": source_system,
            "source_table": source_table,
            "ingestion_run_id": run_id,
            "payload": row,
        }
        for row in rows
    ]

    bronze_bucket = os.environ["S3_BRONZE_BUCKET"]
    artifacts_bucket = os.environ["S3_ARTIFACTS_BUCKET"]

    bronze_key = (
        f"{args.entity}/"
        f"entity_name={args.entity}/"
        f"extraction_date={extraction_date}/"
        f"{run_id}.json"
    )

    _upload_payload(bronze_bucket, bronze_key, envelope_rows)
    write_checkpoint(artifacts_bucket, args.entity, run_ts.isoformat())

    print(
        json.dumps(
            {
                "status": "ok",
                "entity": args.entity,
                "records": len(rows),
                "bronze_bucket": bronze_bucket,
                "bronze_key": bronze_key,
                "run_id": run_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
