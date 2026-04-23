"""embed_docs.py — Indexa docs/ADRs/runbooks no Qdrant local.

Uso:
    python pipelines/rag/embed_docs.py
    python pipelines/rag/embed_docs.py --docs-dir docs --qdrant-url http://localhost:6333

Requer: pip install fastembed qdrant-client
"""
import argparse
import os
import re
from pathlib import Path
from typing import Optional

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

COLLECTION_NAME = "wms_operational_docs"
EMBEDDING_MODEL  = "BAAI/bge-base-en-v1.5"
VECTOR_SIZE      = 768
CHUNK_SIZE       = 800   # chars
CHUNK_OVERLAP    = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doc_type(path: Path) -> str:
    parts = path.parts
    if "adr" in parts:
        return "adr"
    if "runbook" in parts:
        return "runbook"
    if "architecture" in path.stem:
        return "architecture"
    return "doc"


def _chunk(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries."""
    paragraphs = re.split(r"\n{2,}", text.strip())
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > size and current:
            chunks.append(current.strip())
            current = current[-overlap:] + "\n\n" + para
        else:
            current = (current + "\n\n" + para).strip()
    if current:
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 50]


def _title(path: Path, text: str) -> str:
    m = re.search(r"^#\s+(.+)", text, re.MULTILINE)
    return m.group(1).strip() if m else path.stem.replace("-", " ").title()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(docs_dir: str, qdrant_url: str, api_key: Optional[str]) -> None:
    docs_path = Path(docs_dir)
    md_files  = sorted(docs_path.rglob("*.md"))
    print(f"Encontrados {len(md_files)} arquivos Markdown em '{docs_dir}'")

    # Qdrant
    client = QdrantClient(url=qdrant_url, api_key=api_key,
                          check_compatibility=False, timeout=30)
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME in existing:
        client.delete_collection(collection_name=COLLECTION_NAME)
        print(f"Coleção '{COLLECTION_NAME}' removida para reindexação limpa.")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"Coleção '{COLLECTION_NAME}' criada.")

    # Embedding model (download na primeira execução ~130 MB)
    print(f"Carregando modelo {EMBEDDING_MODEL}...")
    model = TextEmbedding(EMBEDDING_MODEL)

    point_id  = 0
    total_chunks = 0

    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            continue

        doc_type = _doc_type(md_file)
        title    = _title(md_file, text)
        source   = str(md_file.relative_to(docs_path.parent))
        chunks   = _chunk(text)

        embeddings = list(model.embed(chunks))
        points = []
        for chunk, emb in zip(chunks, embeddings):
            points.append(PointStruct(
                id=point_id,
                vector=emb.tolist(),
                payload={
                    "doc_type": doc_type,
                    "title":    title,
                    "content":  chunk,
                    "source":   source,
                },
            ))
            point_id += 1

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"  [{doc_type.upper()}] {title} — {len(chunks)} chunks indexados")
        total_chunks += len(chunks)

    print(f"\n✅ Concluído: {len(md_files)} docs, {total_chunks} chunks, {point_id} vetores")
    print(f"   Coleção: {COLLECTION_NAME}  |  Qdrant: {qdrant_url}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir",   default="docs")
    parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://localhost:6333"))
    parser.add_argument("--api-key",    default=os.getenv("QDRANT_API_KEY"))
    args = parser.parse_args()
    main(args.docs_dir, args.qdrant_url, args.api_key)
