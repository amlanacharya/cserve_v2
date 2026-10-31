import pytest
from fastapi.testclient import TestClient
from src.api import app
from src.audit.logger import get_decision_history
from src.orchestrator import SupportOrchestrator


@pytest.fixture
def test_client():
    return TestClient(app)


def test_api_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_orchestrator_escalate_path():
    orchestrator = SupportOrchestrator()
    critical_ticket = {
        "channel": "chat",
        "ticket_id": "ORCH-CRIT-01",
        "message": "URGENT: Entire production database is down! Disaster outage!",
    }
    result = orchestrator.process_ticket(critical_ticket, run_id="TEST-RUN-CRIT")
    assert result.ticket_id == "ORCH-CRIT-01"
    assert result.final_disposition in ("ESCALATED_ROUTER", "ESCALATED_ERROR")
    assert result.final_response is None
    assert result.escalation_packet is not None
    assert result.escalation_packet.ticket_id == "ORCH-CRIT-01"

    # Verify written to audit log
    history = get_decision_history(ticket_id="ORCH-CRIT-01")
    assert len(history) >= 1
    assert history[-1]["routing_action"] == "ESCALATE"


def test_orchestrator_safety_veto_path():
    orchestrator = SupportOrchestrator()
    refund_ticket = {
        "channel": "email",
        "ticket_id": "ORCH-REFUND-01",
        "subject": "Need my refund",
        "body": "I demand a refund immediately, please process my billing adjustment.",
    }
    result = orchestrator.process_ticket(refund_ticket, run_id="TEST-RUN-REFUND")
    assert result.ticket_id == "ORCH-REFUND-01"
    assert result.final_disposition in ("ESCALATED_ROUTER", "ESCALATED_ERROR")
    assert result.final_response is None
    assert result.escalation_packet is not None
    assert "must_not_auto_respond" in result.routing_reason or "refund" in result.routing_reason.lower()


def test_audit_row_records_measured_latency():
    result = SupportOrchestrator().process_ticket(
        {
            "channel": "chat",
            "ticket_id": "ORCH-LATENCY-01",
            "message": "How do I rotate my API key?",
        },
        run_id="TEST-RUN-LATENCY",
    )
    row = get_decision_history(ticket_id="ORCH-LATENCY-01")[-1]
    assert row["latency_ms"] > 0
    # The audit row is written just before the pipeline returns, so it can
    # only be a little shorter than the latency reported to the caller.
    assert row["latency_ms"] <= result.latency_ms


def test_api_process_ticket_endpoint(test_client):
    payload = {
        "channel": "forum",
        "ticket_id": "API-TICKET-01",
        "post_title": "Account locked after password attempts",
        "post_content": "Console returns invalid credentials despite correct password. Account is locked.",
    }
    response = test_client.post("/tickets/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_id"] == "API-TICKET-01"
    assert "final_disposition" in data
    assert "latency_ms" in data

