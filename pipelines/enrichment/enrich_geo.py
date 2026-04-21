"""
Geographic enrichment orchestrator.

Workflow:
    1. Read entity→CEP mapping (static dict or DB override table).
    2. For each CEP, call ViaCEP → get city/state/IBGE code.
    3. Augment with IBGE static data (region, state name, coordinates).
    4. Upsert into bronze.geo_reference.
    5. Determine which UFs are present and fetch Open-Meteo weather
       for the configured look-back window.
    6. Upsert into bronze.weather_daily.

Run standalone:
    python -m pipelines.enrichment.enrich_geo
    python -m pipelines.enrichment.enrich_geo --weather-days 90
    python -m pipelines.enrichment.enrich_geo --dry-run

Environment variables (fallback to defaults):
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import date, timedelta
from typing import Optional

import psycopg2
import psycopg2.extras

from pipelines.enrichment.ibge_client import get_state_info
from pipelines.enrichment.viacep_client import lookup_cep_safe
from pipelines.enrichment.weather_client import WeatherClientError, fetch_weather_for_uf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static entity → CEP mapping
# Represents the known warehouses and depositing companies in the WMS.
# CEPs were resolved by cross-referencing the codigoestabelecimento /
# codigoempresa codes present in the Oracle WMS data.
# ---------------------------------------------------------------------------
ENTITY_CEP_MAP: dict[tuple[str, str], str] = {
    # (entity_type, entity_id): CEP
    # Warehouses (codigoestabelecimento)
    ("warehouse", "WH001"): "01310-100",  # São Paulo - SP (Av. Paulista)
    ("warehouse", "WH002"): "20040-020",  # Rio de Janeiro - RJ (Centro)
    ("warehouse", "WH003"): "30130-110",  # Belo Horizonte - MG (Centro)
    ("warehouse", "WH004"): "80020-180",  # Curitiba - PR (Centro)
    ("warehouse", "WH005"): "40020-010",  # Salvador - BA (Centro)
    ("warehouse", "WH006"): "69005-141",  # Manaus - AM
    ("warehouse", "WH007"): "74003-010",  # Goiânia - GO
    # Companies / depositors (codigodepositante)
    ("company", "DEP001"): "01310-100",  # SP
    ("company", "DEP002"): "20040-020",  # RJ
    ("company", "DEP003"): "30130-110",  # BH
    ("company", "DEP004"): "80020-180",  # Curitiba
    ("company", "DEP005"): "40020-010",  # Salvador
}


def _db_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "wms"),
        user=os.getenv("POSTGRES_USER", "wmsadmin"),
        password=os.getenv("POSTGRES_PASSWORD", "wmsadmin2026"),
    )


# ---------------------------------------------------------------------------
# Geo enrichment
# ---------------------------------------------------------------------------

def enrich_geo_references(dry_run: bool = False) -> list[dict]:
    """
    Resolve all entity CEPs via ViaCEP and return list of enriched rows.
    Upserts into bronze.geo_reference unless dry_run=True.
    """
    rows: list[dict] = []

    for (entity_type, entity_id), cep in ENTITY_CEP_MAP.items():
        viacep = lookup_cep_safe(cep)
        if viacep is None:
            logger.warning("Pulando %s/%s — CEP %s não resolvido", entity_type, entity_id, cep)
            continue

        uf = viacep.get("uf", "")
        state_info = get_state_info(uf)
        ibge_code = viacep.get("ibge", "")

        row = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "cep": viacep.get("cep", cep),
            "logradouro": viacep.get("logradouro") or None,
            "bairro": viacep.get("bairro") or None,
            "localidade": viacep.get("localidade") or None,
            "uf": uf or None,
            "estado": state_info.estado if state_info else None,
            "regiao": state_info.regiao if state_info else None,
            "ibge_code": ibge_code or None,
            "latitude": state_info.lat if state_info else None,
            "longitude": state_info.lon if state_info else None,
        }
        rows.append(row)
        logger.info("Enriquecido: %s/%s → %s/%s (%s)", entity_type, entity_id, row["localidade"], uf, row["regiao"])

    if dry_run:
        logger.info("[dry-run] %d linhas não persistidas", len(rows))
        return rows

    _upsert_geo_references(rows)
    return rows


def _upsert_geo_references(rows: list[dict]) -> None:
    if not rows:
        return

    sql = """
    INSERT INTO bronze.geo_reference (
        entity_type, entity_id, cep, logradouro, bairro, localidade,
        uf, estado, regiao, ibge_code, latitude, longitude, _enriched_at
    ) VALUES (
        %(entity_type)s, %(entity_id)s, %(cep)s, %(logradouro)s, %(bairro)s,
        %(localidade)s, %(uf)s, %(estado)s, %(regiao)s, %(ibge_code)s,
        %(latitude)s, %(longitude)s, now()
    )
    ON CONFLICT (entity_type, entity_id) DO UPDATE SET
        cep          = EXCLUDED.cep,
        logradouro   = EXCLUDED.logradouro,
        bairro       = EXCLUDED.bairro,
        localidade   = EXCLUDED.localidade,
        uf           = EXCLUDED.uf,
        estado       = EXCLUDED.estado,
        regiao       = EXCLUDED.regiao,
        ibge_code    = EXCLUDED.ibge_code,
        latitude     = EXCLUDED.latitude,
        longitude    = EXCLUDED.longitude,
        _enriched_at = now()
    """
    conn = _db_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                psycopg2.extras.execute_batch(cur, sql, rows)
        logger.info("geo_reference: %d linhas upsertadas", len(rows))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Weather enrichment
# ---------------------------------------------------------------------------

def enrich_weather(weather_days: int = 30, dry_run: bool = False) -> int:
    """
    Fetch historical weather for all UFs present in geo_reference (or fallback
    to the UFs from ENTITY_CEP_MAP) for the last `weather_days` days.
    Returns total records upserted.
    """
    ufs = _collect_ufs()
    if not ufs:
        logger.warning("Nenhum UF disponível para enriquecimento de clima")
        return 0

    end_date = date.today() - timedelta(days=1)  # yesterday (archive)
    start_date = end_date - timedelta(days=weather_days - 1)

    total = 0
    all_records: list[dict] = []

    for uf in sorted(ufs):
        try:
            records = fetch_weather_for_uf(uf, start_date, end_date)
            all_records.extend(records)
            total += len(records)
        except WeatherClientError as exc:
            logger.error("Weather falhou para UF %s: %s", uf, exc)

    if dry_run:
        logger.info("[dry-run] %d registros de clima não persistidos", total)
        return total

    _upsert_weather(all_records)
    return total


def _collect_ufs() -> set[str]:
    """Read distinct UFs from bronze.geo_reference; fallback to static map."""
    try:
        conn = _db_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT uf FROM bronze.geo_reference WHERE uf IS NOT NULL")
                rows = cur.fetchall()
        conn.close()
        if rows:
            return {r[0] for r in rows}
    except Exception as exc:
        logger.warning("Não foi possível ler UFs do DB, usando mapa estático: %s", exc)

    # fallback: derive from static map using ibge_client
    ufs: set[str] = set()
    for (_, _), cep in ENTITY_CEP_MAP.items():
        viacep = lookup_cep_safe(cep)
        if viacep and viacep.get("uf"):
            ufs.add(viacep["uf"])
    return ufs


def _upsert_weather(records: list[dict]) -> None:
    if not records:
        return

    sql = """
    INSERT INTO bronze.weather_daily (
        location_uf, weather_date,
        avg_temperature_c, min_temperature_c, max_temperature_c,
        precipitation_mm, weather_condition, wind_speed_kmh,
        _enriched_at
    ) VALUES (
        %(location_uf)s, %(date)s,
        %(avg_temperature_c)s, %(min_temperature_c)s, %(max_temperature_c)s,
        %(precipitation_mm)s, %(weather_condition)s, %(wind_speed_kmh)s,
        now()
    )
    ON CONFLICT (location_uf, weather_date) DO UPDATE SET
        avg_temperature_c = EXCLUDED.avg_temperature_c,
        min_temperature_c = EXCLUDED.min_temperature_c,
        max_temperature_c = EXCLUDED.max_temperature_c,
        precipitation_mm  = EXCLUDED.precipitation_mm,
        weather_condition = EXCLUDED.weather_condition,
        wind_speed_kmh    = EXCLUDED.wind_speed_kmh,
        _enriched_at      = now()
    """
    conn = _db_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                psycopg2.extras.execute_batch(cur, sql, records)
        logger.info("weather_daily: %d registros upsertados", len(records))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    parser = argparse.ArgumentParser(description="Enriquecimento geográfico WMS")
    parser.add_argument("--weather-days", type=int, default=30, help="Dias históricos de clima (padrão: 30)")
    parser.add_argument("--dry-run", action="store_true", help="Não persiste no banco")
    parser.add_argument("--skip-geo", action="store_true", help="Pula enriquecimento de localização")
    parser.add_argument("--skip-weather", action="store_true", help="Pula enriquecimento de clima")
    args = parser.parse_args()

    if not args.skip_geo:
        geo_rows = enrich_geo_references(dry_run=args.dry_run)
        logger.info("Geo: %d entidades enriquecidas", len(geo_rows))

    if not args.skip_weather:
        weather_count = enrich_weather(weather_days=args.weather_days, dry_run=args.dry_run)
        logger.info("Weather: %d registros diários", weather_count)


if __name__ == "__main__":
    main()
