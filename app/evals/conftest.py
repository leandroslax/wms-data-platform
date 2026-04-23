"""DeepEval conftest — shared fixtures for WMS agent evaluation suite.

Setup:
    pip install deepeval
    export ANTHROPIC_API_KEY=...
    export POSTGRES_HOST=localhost   # ou host do seu postgres
    pytest app/evals/ -v
"""
import os
import pytest


@pytest.fixture(scope="session")
def db_url() -> str:
    """PostgreSQL connection URL for the gold schema."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db   = os.getenv("POSTGRES_DB", "wms")
    user = os.getenv("POSTGRES_USER", "wmsadmin")
    pw   = os.getenv("POSTGRES_PASSWORD", "wmsadmin2026")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


@pytest.fixture(scope="session")
def llm_model() -> str:
    return os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
