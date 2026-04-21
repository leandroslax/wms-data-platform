"""
Open-Meteo client — fetches historical daily weather for a given lat/lon range.

API: https://archive-api.open-meteo.com/v1/archive
Free, no API key required. Data since 1940.

Returned variables (daily):
    temperature_2m_mean, temperature_2m_min, temperature_2m_max,
    precipitation_sum, wind_speed_10m_max, weather_code

WMO weather codes (weather_code):
    0           → Céu limpo
    1, 2, 3     → Parcialmente nublado / Nublado
    45, 48      → Neblina
    51-57       → Garoa
    61-67       → Chuva
    71-77       → Neve
    80-82       → Pancadas de chuva
    95, 96, 99  → Trovoada
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_TIMEOUT = 30.0

# WMO code → human-readable Portuguese label
WMO_CODE_LABELS: dict[int, str] = {
    0: "Céu limpo",
    1: "Predominantemente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Neblina",
    48: "Neblina com geada",
    51: "Garoa fraca",
    53: "Garoa moderada",
    55: "Garoa intensa",
    56: "Garoa fraca congelante",
    57: "Garoa intensa congelante",
    61: "Chuva fraca",
    63: "Chuva moderada",
    65: "Chuva forte",
    66: "Chuva fraca congelante",
    67: "Chuva forte congelante",
    71: "Neve fraca",
    73: "Neve moderada",
    75: "Neve forte",
    77: "Grãos de neve",
    80: "Pancadas fracas",
    81: "Pancadas moderadas",
    82: "Pancadas violentas",
    85: "Pancadas de neve fracas",
    86: "Pancadas de neve fortes",
    95: "Trovoada",
    96: "Trovoada com granizo fraco",
    99: "Trovoada com granizo forte",
}


class WeatherClientError(Exception):
    """Raised when Open-Meteo returns an unexpected response."""


def wmo_label(code: Optional[int]) -> Optional[str]:
    """Convert a WMO weather code to a Portuguese label."""
    if code is None:
        return None
    return WMO_CODE_LABELS.get(int(code), f"Código {code}")


def fetch_daily_weather(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[dict]:
    """
    Fetch daily weather records for a lat/lon between start_date and end_date.

    Returns a list of dicts with keys:
        date (date), avg_temperature_c, min_temperature_c, max_temperature_c,
        precipitation_mm, wind_speed_kmh, weather_code (int), weather_condition (str)

    Raises:
        WeatherClientError on API or network failure.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": [
            "temperature_2m_mean",
            "temperature_2m_min",
            "temperature_2m_max",
            "precipitation_sum",
            "wind_speed_10m_max",
            "weather_code",
        ],
        "timezone": "America/Sao_Paulo",
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(OPEN_METEO_ARCHIVE_URL, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        raise WeatherClientError(
            f"Open-Meteo HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        ) from exc
    except httpx.RequestError as exc:
        raise WeatherClientError(f"Erro de rede Open-Meteo: {exc}") from exc

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temp_mean = daily.get("temperature_2m_mean", [])
    temp_min = daily.get("temperature_2m_min", [])
    temp_max = daily.get("temperature_2m_max", [])
    precip = daily.get("precipitation_sum", [])
    wind = daily.get("wind_speed_10m_max", [])
    codes = daily.get("weather_code", [])

    records: list[dict] = []
    for i, d in enumerate(dates):
        code = codes[i] if i < len(codes) else None
        records.append(
            {
                "date": date.fromisoformat(d),
                "avg_temperature_c": temp_mean[i] if i < len(temp_mean) else None,
                "min_temperature_c": temp_min[i] if i < len(temp_min) else None,
                "max_temperature_c": temp_max[i] if i < len(temp_max) else None,
                "precipitation_mm": precip[i] if i < len(precip) else None,
                "wind_speed_kmh": wind[i] if i < len(wind) else None,
                "weather_code": code,
                "weather_condition": wmo_label(code),
            }
        )

    logger.info(
        "Open-Meteo: %d registros para (%.4f, %.4f) de %s a %s",
        len(records), latitude, longitude, start_date, end_date,
    )
    return records


def fetch_weather_for_uf(
    uf: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Convenience wrapper: fetch weather using IBGE state centroid coordinates.
    Adds 'location_uf' key to each record.
    """
    from pipelines.enrichment.ibge_client import get_state_info  # local import

    state = get_state_info(uf)
    if state is None:
        raise WeatherClientError(f"UF desconhecida: {uf!r}")

    records = fetch_daily_weather(state.lat, state.lon, start_date, end_date)
    for r in records:
        r["location_uf"] = uf
    return records
