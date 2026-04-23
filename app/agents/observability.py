"""Observability — LangFuse tracing for WMS agents.

Initializes the LangFuse client and exposes helpers used across the agent layer:
  - get_langfuse()         → singleton Langfuse client (flush on shutdown)
  - get_callback_handler() → LangChain CallbackHandler (passed to CrewAI LLMs)
  - trace_crew_run()       → context manager that wraps a full crew execution

Compatible with langfuse 2.x and 3.x — import paths and trace APIs differ
between major versions; this module detects which is installed and adapts.

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
from typing import Any, Generator

logger = logging.getLogger(__name__)

# ── feature flag ──────────────────────────────────────────────────────────────
_ENABLED = os.getenv("LANGFUSE_ENABLED", "true").lower() != "false"

_langfuse_client = None
_callback_handler = None

# Detected major version of the installed langfuse package (2 or 3).
_LANGFUSE_MAJOR: int | None = None


def _detect_langfuse_version() -> int:
    """Return the major version of the installed langfuse package (2 or 3)."""
    global _LANGFUSE_MAJOR  # noqa: PLW0603
    if _LANGFUSE_MAJOR is not None:
        return _LANGFUSE_MAJOR
    try:
        import importlib.metadata  # noqa: PLC0415

        version_str = importlib.metadata.version("langfuse")
        _LANGFUSE_MAJOR = int(version_str.split(".")[0])
    except Exception:  # noqa: BLE001
        _LANGFUSE_MAJOR = 2  # safe default
    return _LANGFUSE_MAJOR


def _is_configured() -> bool:
    """Return True if LangFuse keys are present and the feature is enabled."""
    return (
        _ENABLED
        and bool(os.getenv("LANGFUSE_PUBLIC_KEY"))
        and bool(os.getenv("LANGFUSE_SECRET_KEY"))
    )


def get_langfuse() -> Any | None:
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
                "LangFuse %s initialized — host: %s",
                _detect_langfuse_version(),
                os.getenv("LANGFUSE_HOST", "http://langfuse:3000"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LangFuse initialization failed (tracing disabled): %s", exc)
            return None

    return _langfuse_client


def get_callback_handler() -> Any | None:
    """Return a LangChain-compatible LangFuse CallbackHandler.

    This handler is passed to CrewAI's LLM instances so every LLM call
    is automatically traced as a generation inside the active trace.

    Supports langfuse 2.x and 3.x import paths:
      - v2: langfuse.langchain.CallbackHandler
      - v3: langfuse.CallbackHandler  (re-exported at top level)

    Returns None if LangFuse is unavailable.
    """
    global _callback_handler  # noqa: PLW0603

    if not _is_configured():
        return None

    if _callback_handler is None:
        pk = os.getenv("LANGFUSE_PUBLIC_KEY")
        sk = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")

        CallbackHandler = None  # noqa: N806

        # Try v2 path first (langfuse.langchain), then v3 top-level export.
        for import_path in (
            ("langfuse.langchain", "CallbackHandler"),
            ("langfuse", "CallbackHandler"),
            ("langfuse.callback", "CallbackHandler"),  # legacy / community forks
        ):
            try:
                import importlib  # noqa: PLC0415

                mod = importlib.import_module(import_path[0])
                CallbackHandler = getattr(mod, import_path[1])  # noqa: N806
                logger.debug("LangFuse CallbackHandler found at %s.%s", *import_path)
                break
            except (ImportError, AttributeError):
                continue

        if CallbackHandler is None:
            logger.warning(
                "LangFuse CallbackHandler not found in any known location — "
                "LLM-level tracing disabled."
            )
            return None

        try:
            _callback_handler = CallbackHandler(
                public_key=pk,
                secret_key=sk,
                host=host,
            )
            logger.info("LangFuse CallbackHandler ready.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("LangFuse CallbackHandler init failed: %s", exc)
            return None

    return _callback_handler


def _create_trace(lf: Any, question: str, session_id: str | None) -> Any | None:
    """Create a LangFuse trace, handling API differences between v2 and v3.

    v2: lf.trace(name=..., input=..., session_id=..., tags=...)
    v3: lf.trace(name=..., input=..., session_id=..., tags=...)  — same signature,
        but some builds use start_trace() or require keyword-only args.
    """
    common_kwargs: dict[str, Any] = {
        "name": "wms-crew-run",
        "input": {"question": question},
        "tags": ["crewai", "wms"],
    }
    if session_id:
        common_kwargs["session_id"] = session_id

    # Prefer .trace() — available in both v2 and most v3 builds.
    if hasattr(lf, "trace"):
        return lf.trace(**common_kwargs)

    # v3 fallback: start_trace() used in some 3.x pre-release builds.
    if hasattr(lf, "start_trace"):
        return lf.start_trace(**common_kwargs)

    logger.warning(
        "Langfuse client has neither .trace() nor .start_trace() — "
        "upgrade langfuse or pin to a compatible version. Trace skipped."
    )
    return None


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
            trace = _create_trace(lf, question, session_id)
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
