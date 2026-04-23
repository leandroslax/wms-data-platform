"""Chat route — natural language interface for WMS operational questions.

Delegates to the 3-agent CrewAI crew:
  AnalystAgent  → SQL query on PostgreSQL gold marts
  ResearchAgent → semantic search on runbooks/ADRs via Qdrant
  ReporterAgent → synthesis into structured Portuguese response

Endpoints
---------
POST /chat
    Synchronous — waits for the full answer (kept for API clients / tests).

POST /chat/stream
    Server-Sent Events — yields progress events as each agent completes,
    then the final answer. Use this endpoint from the browser UI to avoid
    request timeouts on slow crews (15+ LLM calls).

SSE event format (JSON lines, each prefixed with "data: ")::

    data: {"type": "progress", "agent": "AnalystAgent",   "message": "..."}
    data: {"type": "progress", "agent": "ResearchAgent",  "message": "..."}
    data: {"type": "progress", "agent": "ReporterAgent",  "message": "..."}
    data: {"type": "done",     "answer": "<markdown>"}
    data: {"type": "error",    "message": "<error text>"}
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Agent display names for progress events ──────────────────────────────────

_AGENT_LABEL = {
    "analyst":    ("AnalystAgent",   "🔍 Consultando dados do PostgreSQL…"),
    "research":   ("ResearchAgent",  "📚 Buscando documentos operacionais…"),
    "reporter":   ("ReporterAgent",  "✍️  Sintetizando resposta final…"),
}

_STEP_COUNTER: dict[int, int] = {}  # thread-id → step count


# ── Synchronous endpoint (kept for tests / external API clients) ──────────────

@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question about WMS operations",
    description=(
        "Accepts a natural language question and routes it through the "
        "3-agent WMS crew (Analyst → Research → Reporter). "
        "Returns a structured answer in Portuguese. "
        "For browser use prefer POST /chat/stream (SSE)."
    ),
)
def chat(request: ChatRequest) -> ChatResponse:
    """Run the WMS agent crew synchronously and return the full answer."""
    import concurrent.futures  # noqa: PLC0415

    TIMEOUT_SECONDS = 180  # 3 min max — prevents indefinite hangs

    try:
        from app.agents.wms_crew import run_wms_crew  # noqa: PLC0415

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_wms_crew, request.question)
            try:
                answer = future.result(timeout=TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Os agentes demoraram mais de 3 minutos. Tente uma pergunta mais simples.",
                )

        return ChatResponse(answer=answer, question=request.question)

    except HTTPException:
        raise

    except ImportError as exc:
        logger.error("Agent dependencies not installed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent layer not available. Check ANTHROPIC_API_KEY and agent dependencies.",
        ) from exc

    except Exception as exc:
        logger.exception("Agent crew failed for question: %s", request.question)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent crew error: {exc}",
        ) from exc


# ── SSE streaming endpoint ────────────────────────────────────────────────────

@router.post(
    "/stream",
    summary="Ask a WMS question — streaming SSE response",
    description=(
        "Same as POST /chat but returns a Server-Sent Events stream. "
        "Emits progress events as each agent completes its task, "
        "followed by a final 'done' event containing the full answer."
    ),
    response_class=StreamingResponse,
)
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Run the WMS agent crew and stream progress via SSE."""

    loop = asyncio.get_running_loop()
    q: asyncio.Queue[dict] = asyncio.Queue()

    # ── step_callback runs inside the crew thread ─────────────────────────────
    step_count: list[int] = [0]

    def _step_callback(step_output) -> None:  # noqa: ANN001
        """Called by CrewAI after every agent tool-use step."""
        step_count[0] += 1
        n = step_count[0]

        # Map step number to agent label (roughly: steps 1-5 analyst,
        # 6-10 researcher, 11-15 reporter — adjusted by crew max_iter=5)
        if n <= 5:
            agent, base_msg = _AGENT_LABEL["analyst"]
        elif n <= 10:
            agent, base_msg = _AGENT_LABEL["research"]
        else:
            agent, base_msg = _AGENT_LABEL["reporter"]

        event = {"type": "progress", "agent": agent, "step": n, "message": base_msg}
        asyncio.run_coroutine_threadsafe(q.put(event), loop)

    # ── crew thread ───────────────────────────────────────────────────────────
    def _run_crew() -> None:
        try:
            from app.agents.wms_crew import build_wms_crew  # noqa: PLC0415
            from app.agents.observability import trace_crew_run  # noqa: PLC0415

            session_id = str(uuid.uuid4())
            with trace_crew_run(request.question, session_id=session_id) as trace:
                crew = build_wms_crew(request.question, step_callback=_step_callback)
                result = crew.kickoff()
                if trace is not None:
                    try:
                        trace.update(
                            output=result.raw,
                            status_message="success",
                            metadata={
                                "endpoint": "chat_stream",
                                "token_usage": getattr(result, "token_usage", None),
                                "tasks_output": [
                                    getattr(t, "raw", str(t))
                                    for t in getattr(result, "tasks_output", [])
                                ],
                            },
                        )
                    except Exception:  # noqa: BLE001
                        pass
            asyncio.run_coroutine_threadsafe(
                q.put({"type": "done", "answer": result.raw}),
                loop,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming crew failed for question: %s", request.question)
            asyncio.run_coroutine_threadsafe(
                q.put({"type": "error", "message": str(exc)}),
                loop,
            )

    thread = threading.Thread(target=_run_crew, daemon=True)
    thread.start()

    # ── SSE generator (runs in async context) ─────────────────────────────────
    async def _event_generator() -> AsyncIterator[str]:
        # Initial "thinking" event so the client knows the crew started
        yield _sse({"type": "progress", "agent": "Crew", "step": 0,
                    "message": "🚀 Iniciando agentes WMS…"})

        deadline = 300.0  # 5 min total timeout
        elapsed  = 0.0
        ping_interval = 10.0  # keep-alive ping every 10s (prevents Docker/proxy drops)

        while elapsed < deadline:
            try:
                event = await asyncio.wait_for(q.get(), timeout=ping_interval)
            except asyncio.TimeoutError:
                elapsed += ping_interval
                # SSE comment line — invisible to the client but keeps TCP alive
                yield ": ping\n\n"
                continue

            yield _sse(event)
            if event["type"] in ("done", "error"):
                break
        else:
            yield _sse({"type": "error", "message": "Timeout: agentes demoraram mais de 5 minutos."})

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",        # disable nginx buffering
            "Connection": "keep-alive",
        },
    )


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
