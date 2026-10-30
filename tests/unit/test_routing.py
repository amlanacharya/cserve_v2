import pytest
from src.core.models import DocumentChunk
from src.routing.escalation import build_escalation_packet
from src.routing.router import evaluate_route


def test_routing_truth_table():
    # 1. All pass -> AUTO_RESPOND
    action, reason = evaluate_route(
        confidence=0.85,
        top_retrieval_score=0.72,
        urgency="MEDIUM",
        must_not_auto_respond=False,
    )
    assert action == "AUTO_RESPOND"
    assert "Auto-respond eligible" in reason

    # 2. Gate 1 failure: low confidence -> ESCALATE
    action, reason = evaluate_route(
        confidence=0.60,
        top_retrieval_score=0.72,
        urgency="MEDIUM",
        must_not_auto_respond=False,
    )
    assert action == "ESCALATE"
    assert "c=0.60<0.75" in reason

    # 3. Gate 2 failure: low retrieval similarity -> ESCALATE
    action, reason = evaluate_route(
        confidence=0.85,
        top_retrieval_score=0.55,
        urgency="MEDIUM",
        must_not_auto_respond=False,
    )
    assert action == "ESCALATE"
    assert "s_ret=0.55<0.65" in reason

    # 4. Gate 3 failure: CRITICAL urgency -> ESCALATE
    action, reason = evaluate_route(
        confidence=0.85,
        top_retrieval_score=0.72,
        urgency="CRITICAL",
        must_not_auto_respond=False,
    )
    assert action == "ESCALATE"
    assert "urgency==CRITICAL" in reason

    # 5. Gate 4 failure: safety veto -> ESCALATE
    action, reason = evaluate_route(
        confidence=0.85,
        top_retrieval_score=0.72,
        urgency="MEDIUM",
        must_not_auto_respond=True,
    )
    assert action == "ESCALATE"
    assert "must_not_auto_respond==True" in reason

    # 6. Multiple failures: names all failed conditions
    action, reason = evaluate_route(
        confidence=0.50,
        top_retrieval_score=0.40,
        urgency="CRITICAL",
        must_not_auto_respond=True,
    )
    assert action == "ESCALATE"
    assert "c=0.50<0.75" in reason
    assert "s_ret=0.40<0.65" in reason
    assert "urgency==CRITICAL" in reason
    assert "must_not_auto_respond==True" in reason


def test_build_escalation_packet():
    candidate_chunks = [
        DocumentChunk(
            chunk_id="DOC-01#s1",
            doc_id="DOC-01",
            title="Doc 1",
            heading_path="Doc 1 > S1",
            text="Text 1",
            ordinal=0,
            similarity=0.8,
        ),
        DocumentChunk(
            chunk_id="DOC-02#s1",
            doc_id="DOC-02",
            title="Doc 2",
            heading_path="Doc 2 > S1",
            text="Text 2",
            ordinal=0,
            similarity=0.7,
        ),
        DocumentChunk(
            chunk_id="DOC-03#s1",
            doc_id="DOC-03",
            title="Doc 3",
            heading_path="Doc 3 > S1",
            text="Text 3",
            ordinal=0,
            similarity=0.6,
        ),
    ]

    packet = build_escalation_packet(
        ticket_id="TICKET-123",
        final_disposition="ESCALATED_ROUTER",
        routing_reason="Escalated: c=0.50<0.75",
        inferred_intent="unclear_request",
        intent_confidence=0.50,
        intent_alternatives={"billing": 0.2},
        urgency="HIGH",
        candidate_docs=candidate_chunks,
        provider_used="groq",
    )

    assert packet.ticket_id == "TICKET-123"
    assert packet.final_disposition == "ESCALATED_ROUTER"
    # Architectural requirement: attaches top-2 candidate docs
    assert len(packet.candidate_docs) == 2
    assert packet.candidate_docs[0].doc_id == "DOC-01"
    assert packet.candidate_docs[1].doc_id == "DOC-02"

