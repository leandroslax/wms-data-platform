"""
IBGE static mapping — UF → region, state name, and representative coordinates.

No API calls; data is embedded to keep the enrichment pipeline self-contained.
Coordinates are approximate centroids of each state (suitable for choropleth maps).

Source reference: IBGE — Divisão Regional do Brasil (2017).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StateInfo:
    uf: str
    estado: str
    regiao: str
    regiao_sigla: str
    lat: float
    lon: float


# fmt: off
_STATE_DATA: list[dict] = [
    # Norte
    {"uf": "AC", "estado": "Acre",             "regiao": "Norte",    "regiao_sigla": "N",  "lat": -9.0238,  "lon": -70.8120},
    {"uf": "AM", "estado": "Amazonas",         "regiao": "Norte",    "regiao_sigla": "N",  "lat": -3.4168,  "lon": -65.8561},
    {"uf": "AP", "estado": "Amapá",            "regiao": "Norte",    "regiao_sigla": "N",  "lat":  1.4100,  "lon": -51.7700},
    {"uf": "PA", "estado": "Pará",             "regiao": "Norte",    "regiao_sigla": "N",  "lat": -3.7913,  "lon": -52.0048},
    {"uf": "RO", "estado": "Rondônia",         "regiao": "Norte",    "regiao_sigla": "N",  "lat": -10.8311, "lon": -63.3700},
    {"uf": "RR", "estado": "Roraima",          "regiao": "Norte",    "regiao_sigla": "N",  "lat":  1.9900,  "lon": -61.3300},
    {"uf": "TO", "estado": "Tocantins",        "regiao": "Norte",    "regiao_sigla": "N",  "lat": -10.1754, "lon": -48.2982},
    # Nordeste
    {"uf": "AL", "estado": "Alagoas",          "regiao": "Nordeste", "regiao_sigla": "NE", "lat": -9.5713,  "lon": -36.7820},
    {"uf": "BA", "estado": "Bahia",            "regiao": "Nordeste", "regiao_sigla": "NE", "lat": -12.5797, "lon": -41.7007},
    {"uf": "CE", "estado": "Ceará",            "regiao": "Nordeste", "regiao_sigla": "NE", "lat": -5.4984,  "lon": -39.3206},
    {"uf": "MA", "estado": "Maranhão",         "regiao": "Nordeste", "regiao_sigla": "NE", "lat": -4.9609,  "lon": -45.2744},
    {"uf": "PB", "estado": "Paraíba",          "regiao": "Nordeste", "regiao_sigla": "NE", "lat": -7.2399,  "lon": -36.7819},
    {"uf": "PE", "estado": "Pernambuco",       "regiao": "Nordeste", "regiao_sigla": "NE", "lat": -8.8137,  "lon": -36.9541},
    {"uf": "PI", "estado": "Piauí",            "regiao": "Nordeste", "regiao_sigla": "NE", "lat": -7.7183,  "lon": -42.7289},
    {"uf": "RN", "estado": "Rio Grande do Norte", "regiao": "Nordeste", "regiao_sigla": "NE", "lat": -5.8127, "lon": -36.5926},
    {"uf": "SE", "estado": "Sergipe",          "regiao": "Nordeste", "regiao_sigla": "NE", "lat": -10.5741, "lon": -37.3857},
    # Centro-Oeste
    {"uf": "DF", "estado": "Distrito Federal", "regiao": "Centro-Oeste", "regiao_sigla": "CO", "lat": -15.7801, "lon": -47.9292},
    {"uf": "GO", "estado": "Goiás",            "regiao": "Centro-Oeste", "regiao_sigla": "CO", "lat": -15.8270, "lon": -49.8362},
    {"uf": "MS", "estado": "Mato Grosso do Sul", "regiao": "Centro-Oeste", "regiao_sigla": "CO", "lat": -20.7722, "lon": -54.7852},
    {"uf": "MT", "estado": "Mato Grosso",      "regiao": "Centro-Oeste", "regiao_sigla": "CO", "lat": -12.6819, "lon": -56.9211},
    # Sudeste
    {"uf": "ES", "estado": "Espírito Santo",   "regiao": "Sudeste",  "regiao_sigla": "SE", "lat": -19.1834, "lon": -40.3089},
    {"uf": "MG", "estado": "Minas Gerais",     "regiao": "Sudeste",  "regiao_sigla": "SE", "lat": -18.5122, "lon": -44.5550},
    {"uf": "RJ", "estado": "Rio de Janeiro",   "regiao": "Sudeste",  "regiao_sigla": "SE", "lat": -22.9068, "lon": -43.1729},
    {"uf": "SP", "estado": "São Paulo",        "regiao": "Sudeste",  "regiao_sigla": "SE", "lat": -23.5505, "lon": -46.6333},
    # Sul
    {"uf": "PR", "estado": "Paraná",           "regiao": "Sul",      "regiao_sigla": "S",  "lat": -24.8900, "lon": -51.5500},
    {"uf": "RS", "estado": "Rio Grande do Sul","regiao": "Sul",      "regiao_sigla": "S",  "lat": -30.0346, "lon": -51.2177},
    {"uf": "SC", "estado": "Santa Catarina",   "regiao": "Sul",      "regiao_sigla": "S",  "lat": -27.2423, "lon": -50.2189},
]
# fmt: on

# Build index by UF for O(1) lookup
_BY_UF: dict[str, StateInfo] = {
    row["uf"]: StateInfo(**row) for row in _STATE_DATA
}

# IBGE UF codes (used to validate the ibge field from ViaCEP)
IBGE_UF_CODES: dict[str, str] = {
    "12": "AC", "27": "AL", "16": "AP", "13": "AM", "29": "BA",
    "23": "CE", "53": "DF", "32": "ES", "52": "GO", "21": "MA",
    "51": "MT", "50": "MS", "31": "MG", "15": "PA", "25": "PB",
    "41": "PR", "26": "PE", "22": "PI", "33": "RJ", "24": "RN",
    "43": "RS", "11": "RO", "14": "RR", "42": "SC", "35": "SP",
    "28": "SE", "17": "TO",
}


def get_state_info(uf: str) -> Optional[StateInfo]:
    """Return StateInfo for a given UF sigla (e.g. 'SP'), or None if unknown."""
    return _BY_UF.get(uf.upper())


def get_state_info_by_ibge_code(ibge_code: str) -> Optional[StateInfo]:
    """Return StateInfo given a 7-digit IBGE municipality code (first 2 digits = UF)."""
    uf_code = ibge_code[:2] if ibge_code else None
    uf = IBGE_UF_CODES.get(uf_code or "")
    return _BY_UF.get(uf) if uf else None


def list_all_states() -> list[StateInfo]:
    """Return all states sorted by UF."""
    return sorted(_BY_UF.values(), key=lambda s: s.uf)


def list_regions() -> list[str]:
    """Return the 5 macro-regions of Brazil."""
    return sorted({s.regiao for s in _BY_UF.values()})
