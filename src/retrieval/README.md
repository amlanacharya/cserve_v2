# Retrieval Component

## Overview
The `retrieval` package provides semantic chunking and dense vector search across CloudServe documentation articles. It segments Markdown documents along H2/H3 header boundaries and embeds chunks into a persistent ChromaDB vector store backed by sentence-transformers (`all-MiniLM-L6-v2`).

## Interface
- `[src/retrieval/chunker.py:chunk_article]`: `chunk_article(doc_dict: dict[str, Any]) -> list[DocumentChunk]` splits an article by headers, merges sections under 40 tokens into preceding siblings, splits sections over 256 words with 30-word overlaps, and establishes hierarchical heading anchors (`Doc > H2 > H3`).
- `[src/retrieval/chunker.py:chunk_documentation]`: `chunk_documentation(docs_path: str | Path) -> list[DocumentChunk]` parses documentation corpus files and enforces chunk count bounds.
- `[src/retrieval/store.py:index_documentation]`: `index_documentation(docs_path: str | Path | None = None, persist_dir: str | Path | None = None, force: bool = False) -> int` idempotently loads chunks into the ChromaDB `cloudserve_kb` collection.
- `[src/retrieval/store.py:query_documents]`: `query_documents(query_text: str, top_k: int = 3, persist_dir: str | Path | None = None) -> list[DocumentChunk]` executes semantic similarity search, mapping distance into cosine similarity.
- `[src/retrieval/store.py:get_chroma_client]`: `get_chroma_client(persist_dir: str | Path | None = None) -> chromadb.Client` returns client configured with `duckdb+parquet`.

## Invariants
- `[src/retrieval/chunker.py:MIN_CHUNKS, MAX_CHUNKS]`: Standard documentation indexing mandates total chunk volume between 70 and 90 chunks.
- `[src/retrieval/store.py:index_documentation]`: Idempotency check: skips re-embedding if collection count matches expected chunk count unless `force=True`.
- `[src/retrieval/store.py:query_documents]`: Cosine distance is transformed via $\text{similarity} = \max(0.0, \min(1.0, 1.0 - \text{distance}))$, guaranteeing results bounded in $[0.0, 1.0]$.

## Side Effects
- Reads `05_Datasets/documentation.json` from disk.
- Creates and updates ChromaDB vector data at `data/chromadb` (`duckdb+parquet`).
- Downloads or loads the sentence-transformers model `all-MiniLM-L6-v2`.

## Verification
- Run: `pytest tests/unit/test_retrieval.py -v`

