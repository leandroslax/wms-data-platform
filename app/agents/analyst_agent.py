"""AnalystAgent — SQL-first agent for WMS PostgreSQL gold marts.

Responds to quantitative questions about warehouse operations by generating
and executing SQL against the 8 analytical marts in the 'gold' schema.
"""
import os

from crewai import Agent, LLM

from app.agents.tools.postgres_tool import postgres_execute_sql


def build_analyst_agent() -> Agent:
    """Build and return the WMS AnalystAgent."""
    llm = LLM(
        model=f"anthropic/{os.getenv('LLM_MODEL', 'claude-haiku-4-5-20251001')}",
        temperature=0,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

    return Agent(
        role="WMS Data Analyst",
        goal=(
            "Responder perguntas sobre operações do armazém com dados precisos e "
            "atualizados dos marts analíticos do WMS. Sempre usar SQL para obter "
            "números exatos — nunca estimar ou inventar valores."
        ),
        backstory=(
            "Você é um analista sênior especializado em operações de armazém (WMS). "
            "Tem acesso direto ao PostgreSQL com 8 marts analíticos no schema 'gold', "
            "cobrindo produtividade de operadores, saúde do estoque, SLA de pedidos, "
            "performance geográfica e impacto climático. "
            "Seu padrão: entenda a pergunta → identifique o mart correto → "
            "escreva SQL preciso → interprete o resultado em português."
        ),
        tools=[postgres_execute_sql],
        llm=llm,
        max_iter=2,
        verbose=True,
    )


# Singleton para uso direto (ex: FastAPI)
AnalystAgent = build_analyst_agent
