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


class _LangfuseV3Trace:
    """Small adapter that gives LangFuse 3.x spans a trace-like update API."""

    def __init__(self, lf: Any) -> None:
        self._lf = lf

    def update(self, **kwargs: Any) -> None:
        """Update the active v3 trace/span using v2-style kwargs."""
        trace_kwargs: dict[str, Any] = {}
        span_kwargs: dict[str, Any] = {}

        for key in ("output", "metadata"):
            if key in kwargs and kwargs[key] is not None:
                trace_kwargs[key] = kwargs[key]

        for key in ("level", "status_message"):
            if key in kwargs and kwargs[key] is not None:
                span_kwargs[key] = kwargs[key]

        if trace_kwargs:
            self._lf.update_current_trace(**trace_kwargs)
        if span_kwargs:
            self._lf.update_current_span(**span_kwargs)


class _LangfuseV2Trace:
    """Adapter that keeps trace and crew span in sync for LangFuse 2.x."""

    def __init__(self, trace: Any, span: Any | None, question: str) -> None:
        self._trace = trace
        self._span = span
        self._question = question
        self._span_closed = False

    @property
    def id(self) -> str | None:
        """Return the underlying LangFuse trace id."""
        return getattr(self._trace, "id", None) or getattr(self._trace, "trace_id", None)

    def score(self, **kwargs: Any) -> Any:
        """Proxy score creation to the underlying LangFuse trace client."""
        return self._trace.score(**kwargs)

    def update(self, **kwargs: Any) -> None:
        """Update trace and close the crew span when final output is available."""
        self._trace.update(**kwargs)

        span_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key in {"output", "metadata", "level", "status_message"} and value is not None
        }
        if self._span is not None and not self._span_closed and span_kwargs:
            self._span.end(**span_kwargs)
            self._span_closed = True

        if kwargs.get("output") is not None:
            self._record_generation(kwargs)

    def end(self, **kwargs: Any) -> None:
        """Close the span if the caller exits before update(output=...)."""
        if self._span is not None and not self._span_closed:
            self._span.end(**kwargs)
            self._span_closed = True

    def _record_generation(self, kwargs: dict[str, Any]) -> None:
        """Create a summary generation so LangFuse dashboards have model data."""
        metadata = kwargs.get("metadata") if isinstance(kwargs.get("metadata"), dict) else {}
        generation_kwargs: dict[str, Any] = {
            "name": "crew-final-answer",
            "model": os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001"),
            "input": {"question": self._question},
            "output": kwargs.get("output"),
            "metadata": {"source": "crew_summary"},
        }

        token_usage = metadata.get("token_usage")
        usage = _coerce_usage(token_usage)
        if usage:
            generation_kwargs["usage"] = usage

        try:
            generation = self._trace.generation(**generation_kwargs)
            generation.end()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not record LangFuse generation summary: %s", exc)


def _coerce_usage(token_usage: Any) -> dict[str, int] | None:
    """Convert CrewAI token usage objects into LangFuse v2 usage dicts."""
    if token_usage is None:
        return None

    if hasattr(token_usage, "model_dump"):
        raw = token_usage.model_dump()
    elif hasattr(token_usage, "dict"):
        raw = token_usage.dict()
    elif isinstance(token_usage, dict):
        raw = token_usage
    else:
        raw = {
            key: getattr(token_usage, key)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            if hasattr(token_usage, key)
        }

    if not raw:
        return None

    prompt_tokens = raw.get("prompt_tokens") or raw.get("input_tokens")
    completion_tokens = raw.get("completion_tokens") or raw.get("output_tokens")
    total_tokens = raw.get("total_tokens")

    usage: dict[str, int] = {}
    if prompt_tokens is not None:
        usage["input"] = int(prompt_tokens)
    if completion_tokens is not None:
        usage["output"] = int(completion_tokens)
    if total_tokens is not None:
        usage["total"] = int(total_tokens)

    return usage or None


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

    # LangFuse 2.x.
    if hasattr(lf, "trace"):
        return lf.trace(**common_kwargs)

    # Older 3.x pre-release builds.
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
    span_cm = None

    if lf is not None:
        try:
            # LangFuse 3.x removed .trace() and uses OTel-backed spans.
            if hasattr(lf, "start_as_current_span") and not hasattr(lf, "trace"):
                span_cm = lf.start_as_current_span(
                    name="wms-crew-run",
                    input={"question": question},
                    metadata={"session_id": session_id} if session_id else None,
                )
                span_cm.__enter__()
                lf.update_current_trace(
                    name="wms-crew-run",
                    input={"question": question},
                    session_id=session_id,
                    tags=["crewai", "wms"],
                )
                trace = _LangfuseV3Trace(lf)
            else:
                trace = _create_trace(lf, question, session_id)
                if trace is not None and hasattr(trace, "span"):
                    span = trace.span(
                        name="crew-execution",
                        input={"question": question},
                    )
                    trace = _LangfuseV2Trace(trace, span, question)
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
        if span_cm is not None:
            try:
                span_cm.__exit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
        elif trace is not None and hasattr(trace, "end"):
            try:
                trace.end(status_message="finished without final output")
            except Exception:  # noqa: BLE001
                pass
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
