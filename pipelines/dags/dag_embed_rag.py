"""dag_embed_rag — Indexa ADRs/runbooks no Qdrant para o ResearchAgent.

Schedule: semanal aos domingos às 05:00 UTC
Reindexação completa: upsert por ID (idempotente)

Tasks:
    check_qdrant   → verifica conectividade com Qdrant
    embed_docs     → chama embed_docs.py sobre /opt/airflow/pipelines/../docs
    log_collection → loga contagem de vetores na coleção
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

EMBED_SCRIPT = "/opt/airflow/pipelines/rag/embed_docs.py"
DOCS_DIR     = "/opt/airflow/docs"

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def _check_qdrant() -> None:
    from qdrant_client import QdrantClient
    url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    client = QdrantClient(url=url, check_compatibility=False, timeout=10)
    collections = client.get_collections().collections
    print(f"✅ Qdrant conectado: {url} — {len(collections)} coleções")


def _log_collection() -> None:
    from qdrant_client import QdrantClient
    url    = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    client = QdrantClient(url=url, check_compatibility=False, timeout=10)
    try:
        count = client.count(collection_name="wms_operational_docs").count
        print(f"✅ wms_operational_docs: {count} vetores indexados")
    except Exception as e:
        print(f"WARN: {e}")


with DAG(
    dag_id="dag_embed_rag",
    description="Indexa ADRs/runbooks/docs no Qdrant (ResearchAgent RAG)",
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 5 * * 0",   # domingos às 05:00 UTC
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["wms", "rag", "qdrant"],
) as dag:

    check_qdrant = PythonOperator(
        task_id="check_qdrant",
        python_callable=_check_qdrant,
    )

    embed = BashOperator(
        task_id="embed_docs",
        bash_command=(
            f"python {EMBED_SCRIPT} "
            f"--docs-dir {DOCS_DIR} "
            f"--qdrant-url ${{QDRANT_URL:-http://qdrant:6333}}"
        ),
    )

    log_collection = PythonOperator(
        task_id="log_collection_count",
        python_callable=_log_collection,
    )

    check_qdrant >> embed >> log_collection
