import sqlite3
from fastapi.testclient import TestClient
from src.core.models import DocumentChunk
from src.generation.formatter import MACHINE_DISCLAIMER, format_customer_message
from src.routing.priority import compute_priority


def test_envelope_has_disclaimer_and_reference():
    doc = DocumentChunk(chunk_id="c", doc_id="DOC-AUTH-001", title="Resolving invalid credential errors", heading_path="", text="t", ordinal=0)
    msg = format_customer_message("Rotate the key. [DOC-AUTH-001]", ["DOC-AUTH-001"], [doc])
    assert msg.startswith(MACHINE_DISCLAIMER)
    assert msg.endswith("Reference: [DOC-AUTH-001: Resolving invalid credential errors]")


def test_priority_orders_tier_and_urgency():
    assert compute_priority("LOW", "free")[0] < compute_priority("HIGH", "free")[0] < compute_priority("HIGH", "enterprise")[0]
    assert compute_priority("CRITICAL", "enterprise") == (100, "critical")


def test_feedback_endpoint_persists(tmp_path, monkeypatch):
    from src import api
    class S: decision_log_path = str(tmp_path / "d.db")
    monkeypatch.setattr(api, "get_settings", lambda: S())
    r = TestClient(api.app).post("/tickets/T-1/feedback", json={"agent_id": "a1", "agent_tier": "TIER_1", "agent_action": "EDITED_AND_SENT", "customer_csat_score": 4})
    assert r.status_code == 200
    assert sqlite3.connect(S.decision_log_path).execute("select count(*) from agent_feedback").fetchone()[0] == 1
    assert TestClient(api.app).post("/tickets/T-1/feedback", json={"agent_id": "a1", "agent_tier": "BOSS", "agent_action": "ACCEPTED_AS_IS"}).status_code == 422
