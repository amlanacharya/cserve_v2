import os
import re
from pathlib import Path
from typing import Any

# Apply Pydantic v2 shim for ChromaDB 0.3.21
import pydantic
import pydantic.v1

setattr(pydantic, "BaseSettings", pydantic.v1.BaseSettings)

# Patch telemetry in posthog if needed to avoid arg mismatch
try:
    import posthog

    if hasattr(posthog, "capture"):
        _orig_capture = posthog.capture

        def _safe_capture(*args, **kwargs):
            try:
                return _orig_capture(*args, **kwargs)
            except Exception:
                pass

        posthog.capture = _safe_capture
except Exception:
    pass

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings
import chromadb.utils.embedding_functions as ef

# Patch Collection.__init__ for Pydantic v2 compatibility
_orig_collection_init = Collection.__init__


def _patched_collection_init(
    self,
    client: Any,
    name: str,
    embedding_function: Any = None,
    metadata: Any = None,
):
    super(Collection, self).__init__(name=name, metadata=metadata)
    self._client = client
    if embedding_function is not None:
        self._embedding_function = embedding_function
    else:
        self._embedding_function = ef.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )


Collection.__init__ = _patched_collection_init

from src.core.config import get_settings
from src.core.models import DocumentChunk
from src.retrieval.chunker import chunk_documentation

_EMBEDDING_FUNCTION = None
_CLIENTS: dict[str, chromadb.Client] = {}
_COLLECTIONS: dict[str, Any] = {}


def get_embedding_function():
    global _EMBEDDING_FUNCTION
    if _EMBEDDING_FUNCTION is None:
        _EMBEDDING_FUNCTION = ef.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    return _EMBEDDING_FUNCTION


def get_chroma_client(persist_dir: str | Path | None = None) -> chromadb.Client:
    settings = get_settings()
    target_dir = str(Path(persist_dir or settings.chroma_persist_dir).resolve())
    if target_dir not in _CLIENTS:
        os.makedirs(target_dir, exist_ok=True)
        client_settings = ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=target_dir,
            anonymized_telemetry=False,
        )
        _CLIENTS[target_dir] = chromadb.Client(client_settings)
    return _CLIENTS[target_dir]


def get_collection(persist_dir: str | Path | None = None) -> Any:
    settings = get_settings()
    target_dir = str(Path(persist_dir or settings.chroma_persist_dir).resolve())
    key = f"{target_dir}::cloudserve_kb"
    client = get_chroma_client(persist_dir)
    embedding_func = get_embedding_function()
    if key not in _COLLECTIONS:
        _COLLECTIONS[key] = client.get_or_create_collection(
            name="cloudserve_kb",
            metadata={"hnsw:space": "cosine"},
            embedding_function=embedding_func,
        )
    return _COLLECTIONS[key]


def index_documentation(
    docs_path: str | Path | None = None,
    persist_dir: str | Path | None = None,
    force: bool = False,
) -> int:
    """
    Idempotent indexing of 29 documentation articles into ChromaDB:
    - Splits articles into 70-90 header-based semantic chunks.
    - Stores into 'cloudserve_kb' collection with cosine space.
    - Checks count first; skips re-indexing if already populated and not force.
    """
    settings = get_settings()
    docs_file = Path(docs_path or settings.documentation_path)
    client = get_chroma_client(persist_dir)
    collection = get_collection(persist_dir)

    chunks = chunk_documentation(docs_file)
    expected_chunk_count = len(chunks)

    current_count = collection.count()
    if current_count == expected_chunk_count and not force:
        # Idempotent skip for sub-second startup
        return current_count

    # If force or incomplete, delete and re-add
    if current_count > 0:
        target_dir = str(Path(persist_dir or settings.chroma_persist_dir).resolve())
        key = f"{target_dir}::cloudserve_kb"
        client.delete_collection("cloudserve_kb")
        if key in _COLLECTIONS:
            del _COLLECTIONS[key]
        collection = get_collection(persist_dir)

    # Batch add chunks
    chunk_ids = [c.chunk_id for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [
        {
            "doc_id": c.doc_id,
            "title": c.title,
            "heading_path": c.heading_path,
            "ordinal": c.ordinal,
        }
        for c in chunks
    ]

    # Add in batches of 50
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        end = min(i + batch_size, len(chunks))
        collection.add(
            ids=chunk_ids[i:end],
            documents=documents[i:end],
            metadatas=metadatas[i:end],
        )

    client.persist()
    return collection.count()


def query_documents(
    query_text: str,
    top_k: int = 3,
    persist_dir: str | Path | None = None,
) -> list[DocumentChunk]:
    """
    Queries ChromaDB cloudserve_kb collection for top_k relevant DocumentChunks.
    Computes cosine similarity = 1 - cosine_distance.
    """
    collection = get_collection(persist_dir)

    if collection.count() == 0:
        # Index lazily if collection is empty
        index_documentation(persist_dir=persist_dir)

    fetch_k = max(10, top_k)
    results = collection.query(query_texts=[query_text], n_results=fetch_k)

    retrieved: list[DocumentChunk] = []
    if not results or not results["ids"] or not results["ids"][0]:
        return retrieved

    ids = results["ids"][0][:top_k]
    docs = results["documents"][0] if results["documents"] else [""] * len(ids)
    metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
    distances = results["distances"][0] if results["distances"] else [1.0] * len(ids)

    for chunk_id, text, meta, dist in zip(ids, docs, metas, distances):
        # In cosine space, cosine distance = 1 - cosine similarity => similarity = 1 - distance
        similarity = max(0.0, min(1.0, 1.0 - float(dist)))
        retrieved.append(
            DocumentChunk(
                chunk_id=chunk_id,
                doc_id=meta.get("doc_id", chunk_id.split("#")[0]),
                title=meta.get("title", ""),
                heading_path=meta.get("heading_path", ""),
                text=text,
                ordinal=int(meta.get("ordinal", 0)),
                similarity=round(similarity, 4),
            )
        )

    # Sort descending by similarity
    retrieved.sort(key=lambda c: c.similarity if c.similarity is not None else 0.0, reverse=True)
    return retrieved
