import shutil
from pathlib import Path
import pytest
from src.retrieval.chunker import chunk_article, chunk_documentation
from src.retrieval.store import index_documentation, query_documents


def test_chunk_documentation_bounds():
    docs_path = Path("05_Datasets/documentation.json")
    if not docs_path.exists():
        pytest.skip("documentation.json not found")

    chunks = chunk_documentation(docs_path)
    # Architectural requirement: 29 articles yield 70-90 chunks
    assert 70 <= len(chunks) <= 90, f"Expected 70-90 chunks, got {len(chunks)}"

    # Check chunk structure
    for c in chunks:
        assert c.chunk_id is not None
        assert "#" in c.chunk_id
        assert c.doc_id.startswith("DOC-")
        assert c.title != ""
        assert c.heading_path != ""
        assert len(c.text.split()) > 0
        assert c.ordinal >= 0


def test_chunk_single_article():
    sample_doc = {
        "doc_id": "DOC-TEST-001",
        "title": "Test Article for Chunking",
        "category": "testing",
        "content": (
            "# Test Article for Chunking\n\n"
            "This is a preamble section.\n\n"
            "## Section One\n\n"
            "Here is the detailed content of section one with enough words to be meaningful.\n\n"
            "## Section Two\n\n"
            "Here is the content of section two which provides actionable steps.\n\n"
            "## Notes\n\n"
            "Short note under forty words.\n"
        ),
    }
    chunks = chunk_article(sample_doc)
    # The trailing section Notes (<40 words) should be merged into Section Two
    assert len(chunks) == 2
    assert chunks[0].chunk_id == "DOC-TEST-001#section-one"
    assert "preamble" in chunks[0].text
    assert chunks[1].chunk_id == "DOC-TEST-001#section-two"
    assert "Short note under forty words" in chunks[1].text


def test_chromadb_index_and_retrieval(tmp_path):
    persist_dir = tmp_path / "chromadb_test"
    docs_path = Path("05_Datasets/documentation.json")
    if not docs_path.exists():
        pytest.skip("documentation.json not found")

    # Index
    count = index_documentation(docs_path=docs_path, persist_dir=persist_dir)
    assert 70 <= count <= 90

    # Idempotent skip check
    count2 = index_documentation(docs_path=docs_path, persist_dir=persist_dir)
    assert count2 == count

    # Query 1: MFA inquiry -> should retrieve DOC-AUTH-002 with s_ret >= 0.65
    mfa_results = query_documents(
        "Multi-factor authentication setup and recovery. The authenticator code is rejected as invalid or user lost device",
        top_k=3,
        persist_dir=persist_dir,
    )
    assert len(mfa_results) == 3
    top_doc = mfa_results[0]
    assert top_doc.doc_id == "DOC-AUTH-002"
    assert top_doc.similarity is not None
    assert top_doc.similarity >= 0.65

    # Query 2: API key rotation -> should retrieve DOC-AUTH-004 with s_ret >= 0.65
    key_results = query_documents(
        "API key rotation and scope management. A previously working key returns 401 Unauthorized or needs replacing after exposure",
        top_k=3,
        persist_dir=persist_dir,
    )
    assert len(key_results) == 3
    assert key_results[0].doc_id == "DOC-AUTH-004"
    assert key_results[0].similarity is not None
    assert key_results[0].similarity >= 0.65
