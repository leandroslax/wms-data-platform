"""Qdrant semantic search tool for the WMS ResearchAgent.

Searches the 'wms_operational_docs' collection which is fed by the
dag_embed_rag Airflow DAG. Documents include runbooks, ADRs, incidents
and platform documentation.
"""
import os

from crewai.tools import tool
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


COLLECTION_NAME = "wms_operational_docs"
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
VECTOR_SIZE = 768


# ---------------------------------------------------------------------------
# Client and embedding helpers
# ---------------------------------------------------------------------------

def _get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY")
    return QdrantClient(url=url, api_key=api_key)


def _embed(text: str) -> list[float]:
    """Generate embedding with FastEmbed (BAAI/bge-base-en-v1.5, 768 dims)."""
    from fastembed import TextEmbedding

    model = TextEmbedding(EMBEDDING_MODEL)
    return list(model.embed([text]))[0].tolist()


def ensure_collection_exists(client: QdrantClient) -> None:
    """Create collection if it doesn't exist yet (dev/local convenience)."""
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

@tool("WMS Operational Knowledge Search")
def qdrant_semantic_search(question: str) -> str:
    """Search WMS operational knowledge base by semantic meaning.

    Use when the question involves operational context, procedures, known
    issues or architectural decisions — not exact numbers:
    - Runbooks: procedimentos de resposta a incidentes do pipeline
    - ADRs: decisões arquiteturais e justificativas (Iceberg vs Delta,
      DMS vs timestamp, Athena vs Redshift, Kinesis vs Kafka)
    - Incidentes passados: root causes registrados e remediações aplicadas
    - Configurações do Oracle WMS e conectividade FortiGate/VPN
    - Boas práticas e documentação técnica da plataforma

    Args:
        question: Natural language question for semantic similarity search.
    """
    try:
        client = _get_client()
        ensure_collection_exists(client)

        embedding = _embed(question)
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding,
            limit=5,
            with_payload=True,
        )

        if not results:
            return "Nenhum documento relevante encontrado na base de conhecimento operacional."

        docs = []
        for r in results:
            p = r.payload or {}
            doc_type = p.get("doc_type", "doc")
            title = p.get("title", "sem título")
            content = p.get("content", "")
            source = p.get("source", "")
            docs.append(
                f"[{doc_type.upper()}] {title} (score: {r.score:.3f})\n"
                f"Fonte: {source}\n\n"
                f"{content}"
            )

        return "\n\n---\n\n".join(docs)

    except Exception as e:
        return f"Erro ao buscar no Qdrant: {e}"
