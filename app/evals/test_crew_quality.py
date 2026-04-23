"""DeepEval — WMS crew quality evaluation suite.

Metrics evaluated per test case:
  - AnswerRelevancyMetric  : a resposta é relevante para a pergunta?
  - FaithfulnessMetric     : a resposta é fiel ao contexto (dados SQL)?
  - BiasMetric             : a resposta contém viés injustificado?

Each test case runs the full 3-agent crew (Analyst → Research → Reporter)
and evaluates the final answer against the expected output.

Run:
    pytest app/evals/test_crew_quality.py -v --timeout=300

Note: Each test hits the LLM — expect ~30-60s per case.
"""
from __future__ import annotations

import os
import pytest

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, BiasMetric
from deepeval.test_case import LLMTestCase

# ── LLM model for DeepEval judge ─────────────────────────────────────────────
# DeepEval uses OpenAI by default; override to Anthropic via env var.
# Set DEEPEVAL_MODEL=claude-haiku-4-5-20251001 and ANTHROPIC_API_KEY.
_JUDGE_MODEL = os.getenv("DEEPEVAL_MODEL", "gpt-4o-mini")

# ── Thresholds ────────────────────────────────────────────────────────────────
RELEVANCY_THRESHOLD  = 0.7
FAITHFULNESS_THRESHOLD = 0.7
BIAS_THRESHOLD       = 0.5


# ── Helper ────────────────────────────────────────────────────────────────────

def _run_crew(question: str) -> tuple[str, list[str], str | None]:
    """Run the WMS crew and return (final_answer, retrieval_context, trace_id).

    retrieval_context contains the AnalystAgent SQL output — used by
    FaithfulnessMetric to verify the final answer is grounded in data.
    """
    from app.agents.wms_crew import build_wms_crew  # noqa: PLC0415
    from app.agents.observability import trace_crew_run  # noqa: PLC0415

    contexts: list[str] = []
    trace_id: str | None = None

    def _capture_step(step_output) -> None:  # noqa: ANN001
        if hasattr(step_output, "result"):
            contexts.append(str(step_output.result))

    with trace_crew_run(question, session_id="deepeval") as trace:
        trace_id = getattr(trace, "id", None) if trace is not None else None
        crew = build_wms_crew(question, step_callback=_capture_step)
        result = crew.kickoff()
        if trace is not None:
            trace.update(
                output=result.raw,
                status_message="success",
                metadata={"eval_suite": "deepeval"},
            )

    return result.raw, contexts, trace_id


def _publish_langfuse_score(
    trace_id: str | None,
    name: str,
    value: float,
    reason: str | None,
) -> None:
    """Publish a DeepEval metric result to the matching LangFuse trace."""
    if not trace_id or os.getenv("LANGFUSE_ENABLED", "true").lower() == "false":
        return

    try:
        from app.agents.observability import get_langfuse  # noqa: PLC0415

        lf = get_langfuse()
        if lf is None:
            return

        lf.score(
            trace_id=trace_id,
            name=name,
            value=float(value),
            data_type="NUMERIC",
            comment=reason,
        )
        lf.flush()
    except Exception:
        # Evals must fail only on quality gates, not observability plumbing.
        return


def _measure_and_publish(metric, test_case: LLMTestCase, trace_id: str | None, name: str) -> None:  # noqa: ANN001
    """Measure a DeepEval metric and always leave a LangFuse trail on failure."""
    try:
        metric.measure(test_case)
    except Exception as exc:
        _publish_langfuse_score(
            trace_id,
            f"{name}_error",
            0.0,
            f"{type(exc).__name__}: {exc}",
        )
        pytest.fail(
            f"DeepEval judge failed while measuring {name}: {type(exc).__name__}: {exc}"
        )

    _publish_langfuse_score(
        trace_id,
        name,
        float(getattr(metric, "score", 0.0)),
        getattr(metric, "reason", None),
    )


# ── Test cases ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("question,expected_keywords", [
    (
        "Qual o SLA geral de pedidos no último mês?",
        ["SLA", "prazo", "%"],
    ),
    (
        "Quais operadores tiveram maior produtividade esta semana?",
        ["operador", "movimentos", "produtividade"],
    ),
    (
        "Há produtos em risco de stockout?",
        ["ruptura", "estoque", "SKU"],
    ),
])
def test_crew_answer_relevancy(question: str, expected_keywords: list[str]) -> None:
    """A resposta final deve ser relevante para a pergunta."""
    answer, _, trace_id = _run_crew(question)

    metric = AnswerRelevancyMetric(
        threshold=RELEVANCY_THRESHOLD,
        model=_JUDGE_MODEL,
        include_reason=True,
    )
    test_case = LLMTestCase(input=question, actual_output=answer)
    _measure_and_publish(metric, test_case, trace_id, "answer_relevancy")

    assert metric.score >= RELEVANCY_THRESHOLD, (
        f"AnswerRelevancy abaixo do threshold ({metric.score:.2f} < {RELEVANCY_THRESHOLD})\n"
        f"Reason: {metric.reason}"
    )

    # Sanity check: pelo menos 1 keyword esperada na resposta
    lower_answer = answer.lower()
    assert any(kw.lower() in lower_answer for kw in expected_keywords), (
        f"Nenhuma keyword esperada encontrada na resposta.\n"
        f"Esperadas: {expected_keywords}\nResposta: {answer[:300]}"
    )


@pytest.mark.parametrize("question", [
    "Qual o SLA geral de pedidos no último mês?",
    "Qual o total de movimentações no bronze?",
])
def test_crew_faithfulness(question: str) -> None:
    """A resposta final deve ser fiel ao contexto retornado pelos agentes."""
    answer, contexts, trace_id = _run_crew(question)

    if not contexts:
        pytest.skip("Nenhum contexto capturado — step_callback não acionado.")

    metric = FaithfulnessMetric(
        threshold=FAITHFULNESS_THRESHOLD,
        model=_JUDGE_MODEL,
        include_reason=True,
    )
    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
        retrieval_context=contexts,
    )
    _measure_and_publish(metric, test_case, trace_id, "faithfulness")

    assert metric.score >= FAITHFULNESS_THRESHOLD, (
        f"Faithfulness abaixo do threshold ({metric.score:.2f} < {FAITHFULNESS_THRESHOLD})\n"
        f"Reason: {metric.reason}"
    )


@pytest.mark.parametrize("question", [
    "Quais operadores tiveram maior produtividade esta semana?",
    "Há produtos em risco de stockout?",
])
def test_crew_no_bias(question: str) -> None:
    """A resposta final não deve conter viés injustificado."""
    answer, _, trace_id = _run_crew(question)

    metric = BiasMetric(
        threshold=BIAS_THRESHOLD,
        model=_JUDGE_MODEL,
        include_reason=True,
    )
    test_case = LLMTestCase(input=question, actual_output=answer)
    _measure_and_publish(metric, test_case, trace_id, "bias")

    assert metric.score <= BIAS_THRESHOLD, (
        f"Bias acima do threshold ({metric.score:.2f} > {BIAS_THRESHOLD})\n"
        f"Reason: {metric.reason}"
    )
