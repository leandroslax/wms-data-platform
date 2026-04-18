"""
oracle_to_postgres.py — Extrai tabelas do Oracle WMS e carrega direto no PostgreSQL bronze.

Uso:
    python pipelines/extraction/oracle_to_postgres.py --mode full_90d
    python pipelines/extraction/oracle_to_postgres.py --mode incremental
    # ou via Makefile:
    make extract
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import oracledb
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(".env")


# ─── Mapeamento Oracle → PostgreSQL bronze ───────────────────────────────────

@dataclass
class EntitySpec:
    name: str                        # nome no bronze (tabela pg)
    oracle_sql: str                  # query no Oracle
    pg_table: str                    # schema.tabela no PG
    mode: str                        # watermark | snapshot_full
    watermark_column: Optional[str] = None   # coluna Oracle para watermark


ENTITIES: List[EntitySpec] = [
    EntitySpec(
        name="orders_documento",
        pg_table="bronze.orders_documento",
        mode="watermark",
        watermark_column="DATAEMISSAO",
        oracle_sql="""
            SELECT
                SEQUENCIADOCUMENTO,
                NUMERODOCUMENTO,
                SERIEDOCUMENTO,
                TIPODOCUMENTO,
                CODIGOEMPRESA,
                CODIGODEPOSITANTE,
                DATAEMISSAO,
                DATAENTREGA,
                VALORTOTALDOCUMENTO,
                SEQUENCIAINTEGRACAO
            FROM ORAINT.DOCUMENTO
            WHERE DATAEMISSAO >= :start_date
            ORDER BY DATAEMISSAO, SEQUENCIADOCUMENTO
        """,
    ),
    EntitySpec(
        name="inventory_produtoestoque",
        pg_table="bronze.inventory_produtoestoque",
        mode="snapshot_full",
        # WMAS.ESTOQUEPRODUTO: estoque atual por produto/estabelecimento
        # Colunas de meta (ideal/min/max) não existem nesta tabela — ficam NULL
        oracle_sql="""
            SELECT
                TO_CHAR(SEQUENCIAESTOQUE)   AS SEQUENCIAESTOQUE,
                CODIGOPRODUTO,
                TO_CHAR(CODIGOESTABELECIMENTO) AS CODIGOESTABELECIMENTO,
                CODIGOEMPRESA,
                NULL                        AS ESTOQUEIDEAL,
                NULL                        AS ESTOQUEMINIMO,
                QUANTIDADEESTOQUE           AS ESTOQUEMAXIMO,
                NULL                        AS ESTOQUESEGURANCA,
                NULL                        AS PONTOREPOSICAO,
                NULL                        AS CONSUMOMEDIO,
                ESPECIEESTOQUE              AS CLASSEPRODUTO
            FROM WMAS.ESTOQUEPRODUTO
            ORDER BY CODIGOPRODUTO, CODIGOESTABELECIMENTO
        """,
    ),
    EntitySpec(
        name="movements_entrada_saida",
        pg_table="bronze.movements_entrada_saida",
        mode="watermark",
        # DATA_REF = DATAMOVIMENTO quando preenchida, senão DATAEMISSAO
        watermark_column="DATA_REF",
        oracle_sql="""
            SELECT
                TO_CHAR(SEQUENCIACARGAESTOQUE)          AS SEQUENCIAMOVIMENTO,
                CODIGOPRODUTO,
                TO_CHAR(CODIGOESTABELECIMENTO)          AS CODIGOESTABELECIMENTO,
                CODIGODEPOSITANTE,
                NULL                                    AS QUANTIDADEANTERIOR,
                QUANTIDADE                              AS QUANTIDADEATUAL,
                DATAMOVIMENTO,
                DATAEMISSAO,
                COALESCE(DATAMOVIMENTO, DATAEMISSAO)    AS DATA_REF,
                NATUREZAOPERACAO                        AS ESTADOMOVIMENTO,
                NULL                                    AS USUARIO,
                NUMERODOCUMENTO                         AS OBSERVACAO
            FROM ORAINT.CARGAESTOQUE
            WHERE COALESCE(DATAMOVIMENTO, DATAEMISSAO) >= :start_date
            ORDER BY COALESCE(DATAMOVIMENTO, DATAEMISSAO), SEQUENCIACARGAESTOQUE
        """,
    ),
    EntitySpec(
        name="products_snapshot",
        pg_table="bronze.products_snapshot",
        mode="snapshot_full",
        # ORAINT.PRODUTO: cadastro de produtos (sem UNIDADEMEDIDA nesta versão)
        oracle_sql="""
            SELECT
                CODIGOPRODUTO,
                NULL                    AS CODIGOESTABELECIMENTO,
                DESCRICAOPRODUTO,
                NULL                    AS UNIDADEMEDIDA,
                CLASSIFICACAOPRODUTO    AS CLASSEPRODUTO
            FROM ORAINT.PRODUTO
            ORDER BY CODIGOPRODUTO
        """,
    ),
]

# Mapa: coluna Oracle (upper) → coluna PostgreSQL (lower)
def _col_map(oracle_col: str) -> str:
    return oracle_col.lower()


# ─── Conexões ────────────────────────────────────────────────────────────────

def oracle_connect():
    host = os.environ["ORACLE_HOST"]
    port = int(os.environ.get("ORACLE_PORT", "1521"))
    user = os.environ["ORACLE_USER"]
    password = os.environ["ORACLE_PASSWORD"]
    if os.environ.get("ORACLE_SERVICE_NAME"):
        dsn = oracledb.makedsn(host, port, service_name=os.environ["ORACLE_SERVICE_NAME"])
    else:
        dsn = oracledb.makedsn(host, port, sid=os.environ["ORACLE_SID"])
    return oracledb.connect(user=user, password=password, dsn=dsn)


def pg_connect():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "wms"),
        user=os.getenv("POSTGRES_USER", "wmsadmin"),
        password=os.getenv("POSTGRES_PASSWORD", "wmsadmin2026"),
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def normalize_value(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        if v.tzinfo is not None:
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v
    if isinstance(v, date) and not isinstance(v, datetime):
        return datetime.combine(v, dt_time.min)
    return v


WATERMARK_FILE = Path("artifacts/extraction/_watermarks.json")


def load_watermarks() -> Dict[str, str]:
    if not WATERMARK_FILE.exists():
        return {}
    return json.loads(WATERMARK_FILE.read_text())


def save_watermarks(wm: Dict[str, str]) -> None:
    WATERMARK_FILE.parent.mkdir(parents=True, exist_ok=True)
    WATERMARK_FILE.write_text(json.dumps(wm, indent=2, ensure_ascii=False))


# ─── Extração de uma entidade ────────────────────────────────────────────────

def extract_entity(
    spec: EntitySpec,
    mode: str,
    days: int,
    watermarks: Dict[str, str],
    batch_size: int = 2000,
) -> int:
    t0 = time.time()
    print(f"\n{'='*70}")
    print(f"[{spec.name}] modo={mode}")

    params: Dict[str, Any] = {}
    if spec.mode == "watermark":
        if mode == "full_90d":
            start_date = datetime.now() - timedelta(days=days)
        else:
            last = watermarks.get(spec.name)
            start_date = datetime.fromisoformat(last) if last else datetime.now() - timedelta(days=days)
        params["start_date"] = start_date
        print(f"  start_date: {start_date}")

    ora_conn = oracle_connect()
    pg_conn  = pg_connect()
    total    = 0
    max_wm: Optional[datetime] = None

    try:
        with ora_conn.cursor() as cur:
            cur.execute(spec.oracle_sql, params)
            columns = [_col_map(d[0]) for d in cur.description]

            # Monta INSERT com ON CONFLICT DO NOTHING (idempotente)
            placeholders = ", ".join(["%s"] * len(columns))
            col_list     = ", ".join(columns)
            insert_sql   = (
                f"INSERT INTO {spec.pg_table} ({col_list}) "
                f"VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            )

            # Para snapshots full: limpa a tabela antes
            if spec.mode == "snapshot_full":
                with pg_conn.cursor() as pgcur:
                    pgcur.execute(f"TRUNCATE {spec.pg_table}")
                pg_conn.commit()
                print(f"  tabela {spec.pg_table} truncada (snapshot_full)")

            while True:
                batch = cur.fetchmany(batch_size)
                if not batch:
                    break

                rows = []
                for row in batch:
                    vals = [normalize_value(v) for v in row]
                    rows.append(vals)

                    if spec.watermark_column:
                        idx = columns.index(_col_map(spec.watermark_column))
                        v = vals[idx]
                        if isinstance(v, datetime):
                            if max_wm is None or v > max_wm:
                                max_wm = v

                with pg_conn.cursor() as pgcur:
                    psycopg2.extras.execute_batch(pgcur, insert_sql, rows, page_size=500)
                pg_conn.commit()
                total += len(rows)
                print(f"  {total} linhas carregadas...", end="\r")

        if spec.mode == "watermark" and max_wm:
            watermarks[spec.name] = max_wm.isoformat()

        print(f"\n  total: {total} linhas | {time.time()-t0:.1f}s")
        return total

    finally:
        ora_conn.close()
        pg_conn.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode",  choices=["full_90d", "incremental"], default="incremental")
    parser.add_argument("--days",  type=int, default=90)
    parser.add_argument("--batch", type=int, default=2000)
    parser.add_argument("--entity", help="Extrai só esta entidade (opcional)")
    args = parser.parse_args()

    watermarks = load_watermarks()
    t0 = time.time()

    print("=" * 70)
    print(f"Oracle → PostgreSQL Bronze  |  modo={args.mode}")
    print(f"host Oracle : {os.getenv('ORACLE_HOST')}")
    print(f"host PG     : {os.getenv('POSTGRES_HOST','localhost')}:5432")
    print("=" * 70)

    specs = [s for s in ENTITIES if not args.entity or s.name == args.entity]
    results = []

    for spec in specs:
        try:
            n = extract_entity(spec, args.mode, args.days, watermarks, args.batch)
            results.append((spec.name, n, "OK"))
        except Exception as e:
            print(f"\n  [ERRO] {spec.name}: {e}")
            results.append((spec.name, 0, f"ERRO: {e}"))
        finally:
            save_watermarks(watermarks)

    print(f"\n{'='*70}")
    print("RESUMO")
    print(f"{'='*70}")
    for name, rows, status in results:
        print(f"  {name:<35} {rows:>7} linhas   {status}")
    print(f"{'='*70}")
    print(f"  tempo total: {time.time()-t0:.1f}s")
    print(f"  watermarks : {WATERMARK_FILE}")


if __name__ == "__main__":
    main()
