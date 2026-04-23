"""ResearchAgent — Semantic retrieval agent for WMS operational knowledge.

Searches the Qdrant vector store (wms_operational_docs) for runbooks,
ADRs, incidents and documentation relevant to the current question.

Note: LLM callbacks removed — CrewAI 0.100+ / LiteLLM is incompatible with
LangChain CallbackHandlers and returns None silently when they are passed.
Crew-level tracing is handled in wms_crew.py via trace_crew_run().
"""
import os

from crewai import Agent, LLM


def build_research_agent() -> Agent:
    """Build and return the WMS ResearchAgent."""
    from app.agents.tools.qdrant_tool import qdrant_semantic_search  # noqa: PLC0415

    llm = LLM(
        model=f"anthropic/{os.getenv('LLM_MODEL', 'claude-haiku-4-5-20251001')}",
        temperature=0,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

    return Agent(
        role="WMS Operations Researcher",
        goal=(
            "Recuperar contexto operacional relevante da base de conhecimento do WMS: "
            "runbooks de resposta a incidentes, ADRs com justificativas arquiteturais, "
            "incidentes históricos e documentação técnica da plataforma. "
            "Enriquecer análises quantitativas com contexto qualitativo."
        ),
        backstory=(
            "Você é o guardião da memória operacional da plataforma WMS. "
            "Quando o analista encontra uma anomalia ou responde a uma pergunta crítica, "
            "você busca na base semântica os runbooks de resposta, as ADRs relevantes "
            "e os incidentes similares já resolvidos. "
            "Você conecta dados com o conhecimento acumulado do time de engenharia, "
            "evitando que o mesmo problema seja investigado do zero duas vezes."
        ),
        tools=[qdrant_semantic_search],
        llm=llm,
        max_iter=5,
        verbose=True,
    )


# Singleton para uso direto
ResearchAgent = build_research_agent
