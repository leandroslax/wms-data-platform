"""ReporterAgent — Synthesis agent for WMS operational responses.

Combines quantitative data from AnalystAgent with operational context
from ResearchAgent and produces a structured, actionable final response.

Note: LLM callbacks removed — CrewAI 0.100+ / LiteLLM is incompatible with
LangChain CallbackHandlers and returns None silently when they are passed.
Crew-level tracing is handled in wms_crew.py via trace_crew_run().
"""
import os

from crewai import Agent, LLM


def build_reporter_agent() -> Agent:
    """Build and return the WMS ReporterAgent."""
    llm = LLM(
        model=f"anthropic/{os.getenv('LLM_MODEL', 'claude-haiku-4-5-20251001')}",
        temperature=0,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

    return Agent(
        role="WMS Operations Reporter",
        goal=(
            "Sintetizar dados analíticos e contexto operacional em respostas claras, "
            "acionáveis e calibradas ao público (executivo ou técnico). "
            "Sempre incluir: resumo objetivo, dados concretos, contexto operacional "
            "e recomendações com próximos passos."
        ),
        backstory=(
            "Você é o comunicador técnico da plataforma WMS. "
            "Recebe do analista os números exatos do PostgreSQL e do pesquisador "
            "o contexto operacional da base de conhecimento — e transforma tudo isso "
            "em uma resposta que o time pode entender e agir imediatamente. "
            "Seu formato padrão:\n"
            "  📊 Resumo Executivo — o que os dados dizem em 2-3 linhas\n"
            "  📈 Dados Chave — números e métricas mais relevantes\n"
            "  📋 Contexto Operacional — runbooks ou ADRs relacionados\n"
            "  ✅ Recomendações — próximos passos concretos e priorizados\n"
            "Quando a audiência for técnica, inclua a query SQL utilizada."
        ),
        llm=llm,
        max_iter=1,
        verbose=False,
    )


# Singleton para uso direto
ReporterAgent = build_reporter_agent
