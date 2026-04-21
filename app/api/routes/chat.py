"""Chat route — natural language interface for WMS operational questions.

Delegates to the 3-agent CrewAI crew:
  AnalystAgent  → SQL query on PostgreSQL gold marts
  ResearchAgent → semantic search on runbooks/ADRs via Qdrant
  ReporterAgent → synthesis into structured Portuguese response

The endpoint is intentionally synchronous for the MVP.
Long-running queries will be moved to a background task + WebSocket
once the PostgreSQL and Qdrant connections are fully provisioned.
"""
import logging

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question about WMS operations",
    description=(
        "Accepts a natural language question and routes it through the "
        "3-agent WMS crew (Analyst → Research → Reporter). "
        "Returns a structured answer in Portuguese."
    ),
)
def chat(request: ChatRequest) -> ChatResponse:
    """Run the WMS agent crew for a natural language question."""
    try:
        # Lazy import — avoids loading CrewAI/LangChain at cold start
        # if ANTHROPIC_API_KEY is not set (e.g. health-check only deployments).
        from app.agents.wms_crew import run_wms_crew  # noqa: PLC0415

        answer = run_wms_crew(request.question)
        return ChatResponse(answer=answer, question=request.question)

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
