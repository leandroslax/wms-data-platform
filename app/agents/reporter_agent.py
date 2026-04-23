"""ReporterAgent — Synthesis agent for WMS operational responses.

Combines quantitative data from AnalystAgent with operational context
from ResearchAgent and produces a structured, actionable final response.

Every LLM call is traced in LangFuse via the CallbackHandler attached to the LLM.
"""
import os

from crewai import Agent, LLM

from app.agents.observability import get_callback_handler


def build_reporter_agent() -> Agent:
    """Build and return the WMS ReporterAgent."""
    callbacks = []
    handler = get_callback_handler()
    if handler is not None:
        callbacks.append(handler)

    llm = LLM(
        model=f"anthropic/{os.getenv('LLM_MODEL', 'claude-haiku-4-5-20251001')}",
        temperature=0,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        callbacks=callbacks or None,
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
        max_iter=2,
        verbose=True,
    )


# Singleton para uso direto
ReporterAgent = build_reporter_agent
