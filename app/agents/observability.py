"""Observability — LangFuse tracing for WMS agents.

Initializes the LangFuse client and exposes helpers used across the agent layer:
  - get_langfuse()       → singleton Langfuse client (flush on shutdown)
  - get_callback_handler() → LangChain CallbackHandler (passed to CrewAI LLMs)
  - trace_crew_run()     → context manager that wraps a full crew execution

Environment variables (set via docker-compose or .env):
  LANGFUSE_PUBLIC_KEY   default: pk-lf-local
  LANGFUSE_SECRET_KEY   default: sk-lf-local
  LANGFUSE_HOST         default: http://langfuse:3000
  LANGFUSE_ENABLED      default: true  (set to "false" to disable without removing keys)
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

# ── feature flag ──────────────────────────────────────────────────────────────
_ENABLED = os.getenv("LANGFUSE_ENABLED", "true").lower() != "false"

_langfuse_client = None
_callback_handler = None


def _is_configured() -> bool:
    """Return True if LangFuse keys are present and the feature is enabled."""
    return (
        _ENABLED
        and bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
        and bool(os.getenv("LANGFUSE_SECRET_KEY"))
    )


def get_langfuse():
    """Return the singleton Langfuse client, initializing it on first call.

    Returns None if LangFuse is disabled or keys are missing.
    """
    global _langfuse_client  # noqa: PLW0603

    if not _is_configured():
        return None

    if _langfuse_client is None:
        try:
            from langfuse import Langfuse  # noqa: PLC0415

            _langfuse_client = Langfuse(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
            )
            logger.info(
                "LangFuse initialized — host: %s",
                os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LangFuse initialization failed (tracing disabled): %s", exc)
            return None

    return _langfuse_client


def get_callback_handler():
    """Return a LangChain-compatible LangFuse CallbackHandler.

    This handler is passed to CrewAI's LLM instances so every LLM call
    is automatically traced as a generation inside the active trace.

    Returns None if LangFuse is unavailable.
    """
    global _callback_handler  # noqa: PLW0603

    if not _is_configured():
        return None

    if _callback_handler is None:
        try:
            from langfuse.callback import CallbackHandler  # noqa: PLC0415

            _callback_handler = CallbackHandler(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                host=os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
            )
            logger.info("LangFuse CallbackHandler ready.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("LangFuse CallbackHandler init failed: %s", exc)
            return None

    return _callback_handler


@contextmanager
def trace_crew_run(question: str, session_id: str | None = None) -> Generator:
    """Context manager that wraps a full crew execution with a LangFuse trace.

    Usage::

        with trace_crew_run(question, session_id=session_id) as trace:
            result = crew.kickoff()
            if trace:
                trace.update(output=result.raw, status_message="success")

    Args:
        question:   The user question being answered.
        session_id: Optional session identifier (e.g., from the FastAPI request).

    Yields:
        The active LangFuse trace object, or None if tracing is disabled.
    """
    lf = get_langfuse()
    trace = None

    if lf is not None:
        try:
            trace = lf.trace(
                name="wms-crew-run",
                input={"question": question},
                session_id=session_id,
                tags=["crewai", "wms"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not create LangFuse trace: %s", exc)

    try:
        yield trace
    except Exception as exc:
        if trace is not None:
            try:
                trace.update(
                    status_message=f"error: {exc}",
                    level="ERROR",
                )
            except Exception:  # noqa: BLE001
                pass
        raise
    finally:
        if lf is not None:
            try:
                lf.flush()
            except Exception:  # noqa: BLE001
                pass


def flush() -> None:
    """Flush pending LangFuse events — call on application shutdown."""
    lf = get_langfuse()
    if lf is not None:
        try:
            lf.flush()
        except Exception:  # noqa: BLE001
            pass
