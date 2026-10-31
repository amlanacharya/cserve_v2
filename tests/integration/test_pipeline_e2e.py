"""End-to-end pipeline tests through the real LangGraph with stubbed providers.

Only the three provider-touching seams (classify, retrieve, generate) are stubbed;
normalize, routing, guardrails, escalation and audit run for real. No network.
"""
import pytest

import src.classify.cache as cache_mod
from src.audit.logger import get_decision_history
from src.core.models import DocumentChunk
from src.orchestrator import SupportOrchestrator
from src.orchestrator import nodes

DOC = DocumentChunk(
    chunk_id="DOC-API-001#resolution",
    doc_id="DOC-API-001",
    title="Rotating API keys",
    heading_path="Rotating API keys > Resolution",
    text="Open the console, choose API keys, then select rotate to issue a new key.",
    ordinal=0,
    similarity=0.9,
)
GOOD_DRAFT = "Open the console, choose API keys, then select rotate to issue a new key [DOC-API-001]."


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Never touch data/cache/classification_cache.json or leak memory entries."""
    monkeypatch.setattr(cache_mod, "_MEMORY_CACHE", {})
    monkeypatch.setattr(
        cache_mod, "_GLOBAL_CACHE", cache_mod.ClassificationCache(tmp_path / "cls.json")
    )


def stub_pipeline(
    monkeypatch,
    *,
    confidence=0.95,
    urgency="LOW",
    must_not=False,
    provider="groq",
    similarity=0.9,
    draft=GOOD_DRAFT,
    citations=("DOC-API-001",),
):
    monkeypatch.setattr(
        nodes,
        "classify_ticket",
        lambda t: {
            "inferred_intent": "api_key_rotation",
            "intent_alternatives": {},
            "urgency": urgency,
            "confidence": confidence,
            "must_not_auto_respond": must_not,
            "provider_used": provider,
        },
    )
    monkeypatch.setattr(
        nodes,
        "query_documents",
        lambda query_text, top_k: [DOC.model_copy(update={"similarity": similarity})],
    )
    monkeypatch.setattr(
        nodes,
        "generate_response",
        lambda subject, body, retrieved_docs: {
            "draft_response": draft,
            "citations": list(citations),
            "provider_used": provider,
        },
    )


def run(tid):
    return SupportOrchestrator().process_ticket(
        {"channel": "chat", "ticket_id": tid, "message": "How do I rotate my API key?"},
        run_id=f"RUN-{tid}",
    )


def test_auto_respond_path(monkeypatch):
    stub_pipeline(monkeypatch)
    r = run("E2E-AUTO-01")
    assert r.final_disposition == "AUTO_RESOLVED"
    assert r.final_response == GOOD_DRAFT
    assert r.citations == ["DOC-API-001"]
    assert r.escalation_packet is None
    row = get_decision_history(ticket_id="E2E-AUTO-01")[-1]
    assert row["routing_action"] == "AUTO_RESPOND"
    assert row["guardrail_status"] == "PASSED"
    assert row["final_disposition"] == "AUTO_RESOLVED"


@pytest.mark.parametrize(
    "draft,citations,violation",
    [
        ("Contact admin@example.com for the key [DOC-API-001].", ("DOC-API-001",), "PII_EMAIL_DETECTED"),
        (GOOD_DRAFT, ("DOC-NOPE-999",), "HALLUCINATED_DOC_ID"),
        ("Open the console and rotate the key.", (), "MISSING_DOC_CITATIONS"),
    ],
)
def test_guardrail_diverts_to_escalated_guardrail(monkeypatch, draft, citations, violation):
    stub_pipeline(monkeypatch, draft=draft, citations=citations)
    r = run("E2E-GUARD-01")
    assert r.final_disposition == "ESCALATED_GUARDRAIL"
    assert r.final_response is None
    assert r.citations == []
    assert r.escalation_packet is not None
    assert r.escalation_packet.final_disposition == "ESCALATED_GUARDRAIL"
    assert any(violation in v for v in r.escalation_packet.guardrail_violations)
    row = get_decision_history(ticket_id="E2E-GUARD-01")[-1]
    assert row["routing_action"] == "AUTO_RESPOND"
    assert row["guardrail_status"] == "TRIPPED"
    assert violation in str(row["guardrail_violations"])
    assert row["final_disposition"] == "ESCALATED_GUARDRAIL"


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({}, "AUTO_RESOLVED"),
        ({"confidence": 0.74}, "ESCALATED_ROUTER"),
        ({"confidence": 0.75}, "AUTO_RESOLVED"),
        ({"similarity": 0.64}, "ESCALATED_ROUTER"),
        ({"similarity": 0.65}, "AUTO_RESOLVED"),
        ({"urgency": "CRITICAL"}, "ESCALATED_ROUTER"),
        ({"urgency": "HIGH"}, "AUTO_RESOLVED"),
        ({"must_not": True}, "ESCALATED_ROUTER"),
        ({"provider": "offline_mock"}, "ESCALATED_ROUTER"),
    ],
)
def test_routing_truth_table_through_graph(monkeypatch, overrides, expected):
    stub_pipeline(monkeypatch, **overrides)
    r = run("E2E-ROUTE-01")
    assert r.final_disposition == expected
    row = get_decision_history(ticket_id="E2E-ROUTE-01")[-1]
    if expected == "AUTO_RESOLVED":
        assert row["routing_action"] == "AUTO_RESPOND"
        assert r.final_response and r.escalation_packet is None
    else:
        assert row["routing_action"] == "ESCALATE"
        assert r.final_response is None and r.escalation_packet is not None
