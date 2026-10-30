import os
from pathlib import Path
import pytest
from src.core.models import CanonicalTicket, DocumentChunk


@pytest.fixture(autouse=True)
def test_env_setup(tmp_path, monkeypatch):
    """Isolate SQLite database and ChromaDB path per test run."""
    db_file = tmp_path / "test_decision_log.db"
    chroma_dir = tmp_path / "chromadb"
    monkeypatch.setenv("DECISION_LOG_PATH", str(db_file))
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_dir))
    yield


@pytest.fixture
def sample_canonical_ticket():
    return CanonicalTicket(
        ticket_id="TICKET-FIXTURE-01",
        channel="email",
        subject="Container health check failing on deployment",
        body="Our containers fail health checks during deployment and roll back repeatedly.",
    )


@pytest.fixture
def sample_candidate_chunks():
    return [
        DocumentChunk(
            chunk_id="DOC-DEPLOY-001#resolution",
            doc_id="DOC-DEPLOY-001",
            title="Container deployments failing during the health check phase",
            heading_path="Container deployments failing > Resolution",
            text="Confirm the container is listening on the declared port. Increase initial delay.",
            ordinal=0,
            similarity=0.88,
        ),
        DocumentChunk(
            chunk_id="DOC-DEPLOY-002#symptoms",
            doc_id="DOC-DEPLOY-002",
            title="Container crash loop backoff resolution",
            heading_path="Crash loop backoff > Symptoms",
            text="Examine application logs for unhandled exit codes.",
            ordinal=1,
            similarity=0.74,
        ),
    ]

