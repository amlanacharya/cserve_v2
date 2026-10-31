import os
from pathlib import Path
import pytest
import src.classify.cache as cache_mod
from src.classify.cache import ClassificationCache
from src.core.config import get_settings
from src.core.models import CanonicalTicket, DocumentChunk

# Every provider credential read by src/core/config.py.
PROVIDER_KEY_VARS = ("GROQ_API_KEY", "GEMINI_API_KEY")


@pytest.fixture(autouse=True)
def test_env_setup(tmp_path, monkeypatch):
    """Isolate SQLite database and ChromaDB path per test run."""
    db_file = tmp_path / "test_decision_log.db"
    chroma_dir = tmp_path / "chromadb"
    monkeypatch.setenv("DECISION_LOG_PATH", str(db_file))
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_dir))
    yield


@pytest.fixture(autouse=True)
def hermetic_providers(monkeypatch):
    """No provider keys in any test: the cascade falls to the offline heuristic, never the network."""
    for var in PROVIDER_KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def isolated_classification_cache(tmp_path, monkeypatch):
    """Empty in-memory classification cache backed by a tmp file; never touches data/cache."""
    monkeypatch.setattr(cache_mod, "_MEMORY_CACHE", {})
    monkeypatch.setattr(cache_mod, "_GLOBAL_CACHE", ClassificationCache(tmp_path / "cls.json"))


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

