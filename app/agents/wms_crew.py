"""WMS 3-Agent Crew — orchestrates Analyst, Research and Reporter agents.

Entry point for the AI layer of the WMS Data Platform.
Sequential flow: AnalystAgent → ResearchAgent → ReporterAgent.

Usage:
    from app.agents.wms_crew import run_wms_crew

    answer = run_wms_crew("Quais operadores tiveram queda de produtividade esta semana?")
    print(answer)
"""
from crewai import Crew, Task, Process

from app.agents.analyst_agent import build_analyst_agent
from app.agents.research_agent import build_research_agent
from app.agents.reporter_agent import build_reporter_agent


def build_wms_crew(question: str) -> Crew:
    """Build a Crew wired to answer a specific WMS question."""
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

    return Crew(
        agents=[analyst, researcher, reporter],
        tasks=[analysis_task, research_task, report_task],
        process=Process.sequential,
        memory=True,
        verbose=True,
    )


def run_wms_crew(question: str) -> str:
    """Run the WMS 3-agent crew and return the final answer.

    Args:
        question: Natural language question about WMS operations.

    Returns:
        Structured response from the ReporterAgent.
    """
    crew = build_wms_crew(question)
    result = crew.kickoff()
    return result.raw
