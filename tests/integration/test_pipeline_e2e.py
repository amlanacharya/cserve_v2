"""End-to-end pipeline tests through the real LangGraph with stubbed providers.

Only the three provider-touching seams (classify, retrieve, generate) are stubbed;
normalize, routing, guardrails, escalation and audit run for real. No network.
"""
import json

import pytest

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


pytestmark = pytest.mark.usefixtures("isolated_classification_cache")


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


def test_audit_row_logs_retrieval_classification_provider_and_pii(monkeypatch):
    stub_pipeline(monkeypatch, provider="groq")
    monkeypatch.setattr(
        nodes,
        "generate_response",
        lambda subject, body, retrieved_docs: {
            "draft_response": GOOD_DRAFT,
            "citations": ["DOC-API-001"],
            "provider_used": "gemini",
        },
    )
    SupportOrchestrator().process_ticket(
        {"channel": "chat", "ticket_id": "E2E-META-01", "message": "Rotate my key, I am bob@example.com"},
        run_id="RUN-E2E-META-01",
    )
    row = get_decision_history(ticket_id="E2E-META-01")[-1]
    assert row["classification_provider"] == "groq"
    assert row["provider_used"] == "gemini"
    assert json.loads(row["retrieved_doc_ids"]) == ["DOC-API-001"]
    assert row["pii_redactions_count"] == 1


def test_escalated_ticket_still_logs_retrieved_docs(monkeypatch):
    stub_pipeline(monkeypatch, confidence=0.1)
    run("E2E-META-02")
    row = get_decision_history(ticket_id="E2E-META-02")[-1]
    assert row["final_disposition"] == "ESCALATED_ROUTER"
    assert row["citations"] == "[]"
    assert json.loads(row["retrieved_doc_ids"]) == ["DOC-API-001"]


def test_retrieval_k_recorded_per_run_not_read_at_report_time(monkeypatch):
    from src.core.config import get_settings

    stub_pipeline(monkeypatch)
    monkeypatch.setenv("TOP_K_PASSAGES", "2")
    get_settings.cache_clear()
    run("E2E-K-01")
    assert get_decision_history(ticket_id="E2E-K-01")[-1]["retrieval_k"] == 2


def test_classify_crash_is_attributed_to_failed_node_not_a_provider(monkeypatch):
    stub_pipeline(monkeypatch)

    def boom(_ticket):
        raise RuntimeError("simulated classify crash")

    monkeypatch.setattr(nodes, "classify_ticket", boom)
    run("E2E-CRASH-CLS")
    row = get_decision_history(ticket_id="E2E-CRASH-CLS")[-1]
    assert json.loads(row["failed_nodes"]) == ["classify_node"]
    assert row["classification_provider"] is None
    assert row["is_degraded"] == 1


def test_classify_fallback_to_offline_is_attributed_to_offline_provider():
    # no provider keys (conftest): the cascade falls back to the offline heuristic, no crash
    SupportOrchestrator().process_ticket(
        {"channel": "chat", "ticket_id": "E2E-OFFLINE", "message": "How do I rotate my API key?"},
        run_id="RUN-E2E-OFFLINE",
    )
    row = get_decision_history(ticket_id="E2E-OFFLINE")[-1]
    assert row["classification_provider"] == "offline_mock"
    assert row["failed_nodes"] is None


def test_retrieval_crash_is_distinguishable_from_empty_retrieval(monkeypatch):
    stub_pipeline(monkeypatch)

    def boom(query_text, top_k):
        raise RuntimeError("simulated retrieval crash")

    monkeypatch.setattr(nodes, "query_documents", boom)
    result = run("E2E-CRASH-RET")
    row = get_decision_history(ticket_id="E2E-CRASH-RET")[-1]
    assert json.loads(row["failed_nodes"]) == ["retrieval_node"]
    assert row["is_degraded"] == 1
    assert row["retrieved_doc_ids"] == "[]"
    assert "NODE_FAILURE: retrieval_node" in result.routing_reason


def test_healthy_run_has_no_failed_node(monkeypatch):
    stub_pipeline(monkeypatch)
    run("E2E-OK")
    assert get_decision_history(ticket_id="E2E-OK")[-1]["failed_nodes"] is None


def test_classify_then_retrieval_crash_records_both(monkeypatch):
    stub_pipeline(monkeypatch)

    def boom_cls(_ticket):
        raise RuntimeError("simulated classify crash")

    def boom_ret(query_text, top_k):
        raise RuntimeError("simulated retrieval crash")

    monkeypatch.setattr(nodes, "classify_ticket", boom_cls)
    monkeypatch.setattr(nodes, "query_documents", boom_ret)
    result = run("E2E-CRASH-BOTH")
    row = get_decision_history(ticket_id="E2E-CRASH-BOTH")[-1]
    assert json.loads(row["failed_nodes"]) == ["classify_node", "retrieval_node"]
    assert "NODE_FAILURE: classify_node" in result.routing_reason  # first crash still drives routing
