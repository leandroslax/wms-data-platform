from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import oracledb
import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv


@dataclass
class ExportSpec:
    name: str
    sql: str
    mode: str  # watermark | snapshot_full
    watermark_column: Optional[str] = None


EXPORT_SPECS: List[ExportSpec] = [
    ExportSpec(
        name="orders_documento",
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
        name="orders_documentodetalhe",
        mode="watermark",
        watermark_column="DOCUMENTO_DATAEMISSAO",
        sql="""
            SELECT
                d.*,
                h.DATAEMISSAO AS DOCUMENTO_DATAEMISSAO,
                h.DATAMOVIMENTO AS DOCUMENTO_DATAMOVIMENTO,
                h.TIPODOCUMENTO AS DOCUMENTO_TIPODOCUMENTO,
                h.NUMERODOCUMENTO AS DOCUMENTO_NUMERODOCUMENTO,
                h.CODIGOEMPRESA AS DOCUMENTO_CODIGOEMPRESA,
                h.CNPJCPFDESTINO AS DOCUMENTO_CNPJCPFDESTINO,
                h.NOMEDESTINO AS DOCUMENTO_NOMEDESTINO,
                h.UFDESTINO AS DOCUMENTO_UFDESTINO
            FROM ORAINT.DOCUMENTODETALHE d
            JOIN ORAINT.DOCUMENTO h
              ON d.SEQUENCIAINTEGRACAO = h.SEQUENCIAINTEGRACAO
             AND d.SEQUENCIADOCUMENTO = h.SEQUENCIADOCUMENTO
            WHERE h.DATAEMISSAO >= :start_date
            ORDER BY h.DATAEMISSAO, d.SEQUENCIADOCUMENTO, d.SEQUENCIADETALHE
        """.strip(),
    ),
    ExportSpec(
        name="movements_cargaestoque",
        mode="watermark",
        watermark_column="DATA_MOVIMENTO_REF",
        sql="""
            SELECT
                c.*,
                COALESCE(c.DATAMOVIMENTO, c.DATAEMISSAO) AS DATA_MOVIMENTO_REF
            FROM ORAINT.CARGAESTOQUE c
            WHERE COALESCE(c.DATAMOVIMENTO, c.DATAEMISSAO) >= :start_date
            ORDER BY COALESCE(c.DATAMOVIMENTO, c.DATAEMISSAO), c.SEQUENCIACARGAESTOQUE
        """.strip(),
    ),
    ExportSpec(
        name="logistics_romaneio",
        mode="watermark",
        watermark_column="DATAPREVISAOMOVIMENTO",
        sql="""
            SELECT *
            FROM ORAINT.ROMANEIO
            WHERE DATAPREVISAOMOVIMENTO >= :start_date
            ORDER BY DATAPREVISAOMOVIMENTO, SEQUENCIAROMANEIO
        """.strip(),
    ),
    ExportSpec(
        name="logistics_volume",
        mode="watermark",
        watermark_column="DATAATUALIZACAO",
        sql="""
            SELECT *
            FROM ORAINT.VOLUME
            WHERE DATAATUALIZACAO >= :start_date
            ORDER BY DATAATUALIZACAO, SEQUENCIAVOLUME
        """.strip(),
    ),
    ExportSpec(
        name="inventory_snapshot",
        mode="snapshot_full",
        sql="""
            SELECT *
            FROM ORAINT.INVENTARIO
            ORDER BY CODIGOINVENTARIO, SEQUENCIAETIQUETA
        """.strip(),
    ),
    ExportSpec(
        name="products_snapshot",
        mode="snapshot_full",
        sql="""
            SELECT *
            FROM ORAINT.PRODUTO
            ORDER BY CODIGOPRODUTO
        """.strip(),
    ),
    ExportSpec(
        name="movimentoestoque_snapshot",
        mode="snapshot_full",
        sql="""
            SELECT *
            FROM ORAINT.MOVIMENTOESTOQUE
            ORDER BY SEQUENCIAMOVIMENTOESTOQUE
        """.strip(),
    ),
]


def normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, dt_time.min)
    return value


def normalize_row(columns: List[str], row: Iterable[Any]) -> Dict[str, Any]:
    return {columns[idx]: normalize_value(value) for idx, value in enumerate(row)}


def load_watermarks(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_watermarks(path: Path, payload: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def watermark_to_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def build_connection():
    host = os.environ["ORACLE_HOST"]
    port = int(os.environ.get("ORACLE_PORT", "1521"))
    user = os.environ["ORACLE_USER"]
    password = os.environ["ORACLE_PASSWORD"]

    if os.environ.get("ORACLE_SERVICE_NAME"):
        dsn = oracledb.makedsn(host, port, service_name=os.environ["ORACLE_SERVICE_NAME"])
    else:
        dsn = oracledb.makedsn(host, port, sid=os.environ["ORACLE_SID"])

    return oracledb.connect(user=user, password=password, dsn=dsn)


def fmt_seconds(seconds: float) -> str:
    return f"{seconds:.1f}s"


def export_spec(
    spec: ExportSpec,
    mode: str,
    days: int,
    output_root: Path,
    watermarks: Dict[str, str],
    batch_size: int = 5000,
) -> Dict[str, Any]:
    entity_start = time.time()
    now_utc = datetime.now(timezone.utc)
    extract_date = now_utc.strftime("%Y-%m-%d")
    run_ts = now_utc.strftime("%Y%m%dT%H%M%SZ")

    entity_dir = output_root / spec.name / f"extract_date={extract_date}" / f"run_id={run_ts}"
    entity_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = entity_dir / f"{spec.name}.parquet"

    params: Dict[str, Any] = {}
    effective_mode = spec.mode if mode == "incremental" else ("watermark" if spec.mode == "watermark" else "snapshot_full")

    if effective_mode == "watermark":
        if mode == "full_90d":
            start_date = datetime.now() - timedelta(days=days)
        else:
            last_value = watermarks.get(spec.name)
            if last_value:
                start_date = watermark_to_datetime(last_value)
            else:
                start_date = datetime.now() - timedelta(days=days)
        params["start_date"] = start_date

    print("\n" + "=" * 100)
    print(f"[START] {spec.name}")
    print(f"  modo..............: {mode}")
    print(f"  estratégia........: {spec.mode}")
    if params:
        print(f"  start_date........: {params['start_date']}")
    print(f"  saída.............: {parquet_path}")
    print(f"  batch_size........: {batch_size}")

    total_rows = 0
    batch_number = 0
    max_watermark_value: Optional[datetime] = None
    writer: Optional[pq.ParquetWriter] = None

    with build_connection() as conn:
        with conn.cursor() as cur:
            print("  executando query..")
            cur.execute(spec.sql, params)
            columns = [desc[0] for desc in cur.description]
            print(f"  colunas...........: {len(columns)}")

            while True:
                batch = cur.fetchmany(batch_size)
                if not batch:
                    break

                batch_number += 1
                batch_start = time.time()

                rows = [normalize_row(columns, row) for row in batch]
                table = pa.Table.from_pylist(rows)

                if writer is None:
                    writer = pq.ParquetWriter(str(parquet_path), table.schema, compression="snappy")

                writer.write_table(table)
                total_rows += len(rows)

                if spec.watermark_column:
                    for row in rows:
                        value = row.get(spec.watermark_column)
                        if isinstance(value, datetime):
                            if max_watermark_value is None or value > max_watermark_value:
                                max_watermark_value = value

                batch_elapsed = time.time() - batch_start
                print(
                    f"  lote {batch_number:04d}........: "
                    f"{len(rows)} linhas | acumulado={total_rows} | tempo={fmt_seconds(batch_elapsed)}"
                )

    if writer is not None:
        writer.close()

    if total_rows == 0:
        if parquet_path.exists():
            parquet_path.unlink()
        elapsed = time.time() - entity_start
        print("  registros.........: 0")
        print("  status............: sem dados")
        print(f"[END] {spec.name} em {fmt_seconds(elapsed)}")
        return {
            "entity": spec.name,
            "rows": 0,
            "path": None,
            "watermark": watermarks.get(spec.name),
            "elapsed_seconds": round(elapsed, 2),
        }

    if spec.mode == "watermark" and max_watermark_value is not None:
        watermarks[spec.name] = max_watermark_value.isoformat()

    elapsed = time.time() - entity_start
    print(f"  registros.........: {total_rows}")
    if spec.mode == "watermark":
        print(f"  watermark.........: {watermarks.get(spec.name)}")
    print(f"[END] {spec.name} em {fmt_seconds(elapsed)}")

    return {
        "entity": spec.name,
        "rows": total_rows,
        "path": str(parquet_path),
        "watermark": watermarks.get(spec.name),
        "elapsed_seconds": round(elapsed, 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full_90d", "incremental"], default="full_90d")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--output-dir", default="artifacts/parquet_export")
    parser.add_argument("--env-file", default=".env.extract.prod")
    parser.add_argument("--batch-size", type=int, default=5000)
    args = parser.parse_args()

    run_start = time.time()

    load_dotenv(args.env_file)

    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    watermark_path = output_root / "_state" / "oraint_watermarks.json"
    watermarks = load_watermarks(watermark_path)

    print("=" * 100)
    print("EXPORT ORAINT -> PARQUET")
    print(f"modo...............: {args.mode}")
    print(f"janela full........: {args.days} dias")
    print(f"output.............: {output_root}")
    print(f"watermarks.........: {watermark_path}")
    print("=" * 100)

    results = []
    for idx, spec in enumerate(EXPORT_SPECS, start=1):
        print(f"\n[{idx}/{len(EXPORT_SPECS)}] processando entidade...")
        result = export_spec(
            spec=spec,
            mode=args.mode,
            days=args.days,
            output_root=output_root,
            watermarks=watermarks,
            batch_size=args.batch_size,
        )
        results.append(result)
        save_watermarks(watermark_path, watermarks)

    save_watermarks(watermark_path, watermarks)

    summary_path = output_root / "_state" / "last_run_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    total_elapsed = time.time() - run_start

    print("\n" + "=" * 100)
    print("RESUMO FINAL")
    print("-" * 100)
    for item in results:
        print(
            f"{item['entity']:<28} "
            f"rows={item['rows']:<8} "
            f"time={item['elapsed_seconds']:<8}s "
            f"path={item['path']}"
        )
    print("-" * 100)
    print(f"tempo total........: {fmt_seconds(total_elapsed)}")
    print(f"watermarks.........: {watermark_path}")
    print(f"resumo.............: {summary_path}")
    print("=" * 100)


if __name__ == "__main__":
    main()
