"""
ViaCEP client — resolves a Brazilian CEP to address fields.

API: https://viacep.com.br/ws/{cep}/json/
Free, no authentication required.
Rate: ~unlimited for reasonable usage.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

VIACEP_BASE_URL = "https://viacep.com.br/ws"
DEFAULT_TIMEOUT = 10.0
DEFAULT_RETRY_DELAY = 2.0
MAX_RETRIES = 3


class ViaCEPError(Exception):
    """Raised when ViaCEP returns an error or unexpected response."""


def _clean_cep(cep: str) -> str:
    """Remove non-digits and validate length."""
    digits = "".join(c for c in cep if c.isdigit())
    if len(digits) != 8:
        raise ValueError(f"CEP inválido (deve ter 8 dígitos): {cep!r}")
    return digits


def lookup_cep(cep: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """
    Query ViaCEP and return the full address dict.

    Returns a dict with keys:
        cep, logradouro, complemento, bairro, localidade, uf,
        ibge, gia, ddd, siafi

    Raises:
        ViaCEPError  — CEP not found or API error
        ValueError   — invalid CEP format
    """
    clean = _clean_cep(cep)
    url = f"{VIACEP_BASE_URL}/{clean}/json/"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

                if data.get("erro"):
                    raise ViaCEPError(f"CEP não encontrado: {cep}")

                logger.debug("ViaCEP OK — %s → %s/%s", clean, data.get("localidade"), data.get("uf"))
                return data

        except ViaCEPError:
            raise
        except httpx.HTTPStatusError as exc:
            if attempt == MAX_RETRIES:
                raise ViaCEPError(f"HTTP {exc.response.status_code} para CEP {cep}") from exc
            logger.warning("ViaCEP tentativa %d/%d falhou (%s), aguardando...", attempt, MAX_RETRIES, exc)
            time.sleep(DEFAULT_RETRY_DELAY * attempt)
        except httpx.RequestError as exc:
            if attempt == MAX_RETRIES:
                raise ViaCEPError(f"Erro de rede ao consultar CEP {cep}: {exc}") from exc
            logger.warning("ViaCEP tentativa %d/%d — erro de rede, aguardando...", attempt, MAX_RETRIES)
            time.sleep(DEFAULT_RETRY_DELAY * attempt)

    raise ViaCEPError(f"Esgotadas {MAX_RETRIES} tentativas para CEP {cep}")


def lookup_cep_safe(cep: str) -> Optional[dict]:
    """
    Like lookup_cep but returns None instead of raising on failure.
    Suitable for bulk enrichment where some CEPs may be invalid.
    """
    try:
        return lookup_cep(cep)
    except (ViaCEPError, ValueError) as exc:
        logger.warning("ViaCEP ignorado — %s: %s", cep, exc)
        return None
