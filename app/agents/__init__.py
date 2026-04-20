"""WMS AI Agents package.

Three-agent crew for operational analytics and knowledge retrieval:
- AnalystAgent: SQL-first analysis over Redshift Serverless marts
- ResearchAgent: semantic retrieval from Qdrant operational docs
- ReporterAgent: synthesis of data + context into actionable responses

Entry point:
    from app.agents import run_wms_crew
    answer = run_wms_crew("Quais operadores tiveram queda de produtividade esta semana?")
"""
from app.agents.wms_crew import run_wms_crew

__all__ = ["run_wms_crew"]
