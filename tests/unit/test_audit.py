import sqlite3
import pytest
from src.audit.logger import AuditLogger


def test_audit_logger_append_and_immutability(tmp_path):
    db_file = tmp_path / "test_decision_log.db"
    audit = AuditLogger(db_file)

    record = {
        "run_id": "RUN-001",
        "ticket_id": "TICKET-001",
        "channel": "email",
        "inferred_intent": "api_key_issue",
        "intent_confidence": 0.85,
        "intent_alternatives": {"auth": 0.1},
        "urgency": "MEDIUM",
        "top_retrieval_score": 0.75,
        "must_not_auto_respond": False,
        "routing_action": "AUTO_RESPOND",
        "routing_reason": "All gates passed",
        "guardrail_status": "PASSED",
        "final_disposition": "AUTO_RESOLVED",
        "citations": ["DOC-AUTH-004"],
        "provider_used": "groq",
        "is_degraded": False,
        "error_details": None,
        "latency_ms": 250.5,
    }

    # 1. Log decision
    audit.log_decision(record)
    history = audit.get_decision_history(run_id="RUN-001")
    assert len(history) == 1
    row = history[0]
    assert row["ticket_id"] == "TICKET-001"
    assert row["channel"] == "email"
    assert row["final_disposition"] == "AUTO_RESOLVED"
    assert row["intent_confidence"] == 0.85

    # 2. Verify append-only UPDATE trigger raises exception
    with pytest.raises(sqlite3.IntegrityError, match="decision_log is append-only"):
        with sqlite3.connect(str(db_file)) as conn:
            conn.execute("UPDATE decision_log SET final_disposition = 'CORRUPTED' WHERE id = ?", (row["id"],))

    # 3. Verify append-only DELETE trigger raises exception
    with pytest.raises(sqlite3.IntegrityError, match="decision_log is append-only"):
        with sqlite3.connect(str(db_file)) as conn:
            conn.execute("DELETE FROM decision_log WHERE id = ?", (row["id"],))

    # Verify data is still intact
    history_after = audit.get_decision_history(run_id="RUN-001")
    assert len(history_after) == 1
    assert history_after[0]["final_disposition"] == "AUTO_RESOLVED"

