"""WMS 3-Agent Crew — orchestrates Analyst, Research and Reporter agents.

Entry point for the AI layer of the WMS Data Platform.
Sequential flow: AnalystAgent → ResearchAgent → ReporterAgent.

Every crew run is traced in LangFuse (self-hosted at localhost:3001).
Tracing is optional — if LangFuse is unavailable the crew runs normally.

Usage:
    from app.agents.wms_crew import run_wms_crew

    answer = run_wms_crew("Quais operadores tiveram queda de produtividade esta semana?")
    print(answer)
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Callable, Optional

from crewai import Crew, Task, Process

from app.agents.analyst_agent import build_analyst_agent
from app.agents.research_agent import build_research_agent
from app.agents.reporter_agent import build_reporter_agent
from app.agents.observability import trace_crew_run

logger = logging.getLogger(__name__)

# CrewAI memory usa Chroma com embeddings OpenAI (requer OPENAI_API_KEY com créditos ativos).
# Desativado por padrão — habilitar via env var CREWAI_MEMORY=true quando a chave tiver créditos.
_MEMORY_ENABLED = os.getenv("CREWAI_MEMORY", "false").lower() == "true"
logger.info("CrewAI memory: %s", "ATIVADA" if _MEMORY_ENABLED else "desativada (CREWAI_MEMORY != true)")


def build_wms_crew(
    question: str,
    step_callback: Optional[Callable] = None,
) -> Crew:
    """Build a Crew wired to answer a specific WMS question.

    Args:
        question: Natural language question about WMS operations.
        step_callback: Optional callable invoked after each agent step.
                       Receives a string description of the completed step.
    """
    analyst = build_analyst_agent()
    researcher = build_research_agent()
    reporter = build_reporter_agent()

    analysis_task = Task(
        description=(
            f"Analise a seguinte pergunta sobre operações do WMS e responda "
            f"com dados precisos do PostgreSQL (schema gold):\n\n"
            f"PERGUNTA: {question}\n\n"
            "Identifique o(s) mart(s) correto(s) no schema 'gold', escreva a query SQL adequada, "
            "execute-a e interprete os resultados. Inclua a query utilizada na resposta."
        ),
        expected_output=(
            "Dados quantitativos do PostgreSQL com: query SQL executada, "
            "resultados tabulados e interpretação inicial em português."
        ),
        agent=analyst,
    )

    research_task = Task(
        description=(
            f"Com base na pergunta abaixo e nos dados quantitativos levantados, "
            f"busque contexto operacional relevante na base de conhecimento WMS:\n\n"
            f"PERGUNTA ORIGINAL: {question}\n\n"
            "Procure runbooks, ADRs ou incidentes passados relacionados ao tema. "
            "Se não houver documentos relevantes, diga explicitamente."
        ),
        expected_output=(
            "Documentos operacionais relevantes com título, tipo (runbook/ADR/incidente) "
            "e conteúdo. Score de similaridade para cada documento."
        ),
        agent=researcher,
        context=[analysis_task],
    )

    report_task = Task(
        description=(
            f"Sintetize os dados analíticos e o contexto operacional em uma resposta "
            f"final clara e acionável para a pergunta:\n\n"
            f"PERGUNTA ORIGINAL: {question}\n\n"
            "Use o formato padrão: Resumo Executivo | Dados Chave | "
            "Contexto Operacional | Recomendações."
        ),
        expected_output=(
            "Resposta estruturada em português com: resumo executivo (2-3 linhas), "
            "dados chave com números, contexto operacional (runbooks/ADRs), "
            "e recomendações priorizadas com próximos passos."
        ),
        agent=reporter,
        context=[analysis_task, research_task],
    )

    crew_kwargs: dict = dict(
        agents=[analyst, researcher, reporter],
        tasks=[analysis_task, research_task, report_task],
        process=Process.sequential,
        memory=_MEMORY_ENABLED,
        verbose=True,
    )
    if step_callback is not None:
        crew_kwargs["step_callback"] = step_callback

    return Crew(**crew_kwargs)


def run_wms_crew(question: str, session_id: str | None = None) -> str:
    """Run the WMS 3-agent crew and return the final answer.

    Every run is traced in LangFuse automatically. Tracing failures are
    caught silently so they never break the crew execution.

    Args:
        question:   Natural language question about WMS operations.
        session_id: Optional session ID for LangFuse grouping (e.g. FastAPI request ID).

    Returns:
        Structured response from the ReporterAgent.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    with trace_crew_run(question, session_id=session_id) as trace:
        crew = build_wms_crew(question)
        result = crew.kickoff()
        answer = result.raw

        if trace is not None:
            try:
                trace.update(
                    output=answer,
                    status_message="success",
                    metadata={
                        "token_usage": getattr(result, "token_usage", None),
                        "tasks_output": [
                            getattr(t, "raw", str(t))
                            for t in getattr(result, "tasks_output", [])
                        ],
                    },
                )
            except Exception:  # noqa: BLE001
                pass

    return answer
