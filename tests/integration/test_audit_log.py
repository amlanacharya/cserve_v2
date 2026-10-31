import sqlite3
import pytest
from src.audit.logger import AuditLogger, get_decision_history, log_decision


def test_audit_log_reconciliation_and_triggers(tmp_path):
    db_path = tmp_path / "reconciliation.db"
    audit = AuditLogger(db_path)
    run_id = "BATCH-REC-001"
    ticket_count = 10

    # 1. Log 10 decisions
    for i in range(ticket_count):
        record = {
            "run_id": run_id,
            "ticket_id": f"REC-TICKET-{i:03d}",
            "channel": "email" if i % 2 == 0 else "chat",
            "inferred_intent": "api_key_issue",
            "intent_confidence": 0.82,
            "intent_alternatives": {"auth": 0.1},
            "urgency": "MEDIUM",
            "top_retrieval_score": 0.77,
            "must_not_auto_respond": False,
            "routing_action": "AUTO_RESPOND",
            "routing_reason": "Dual gates passed",
            "guardrail_status": "PASSED",
            "final_disposition": "AUTO_RESOLVED",
            "citations": ["DOC-AUTH-004"],
            "provider_used": "groq",
            "is_degraded": False,
            "error_details": None,
            "latency_ms": 120.0,
        }
        audit.log_decision(record)

    # 2. Assert exact row count matches input ticket count
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM decision_log WHERE run_id = ?", (run_id,))
        count = cursor.fetchone()[0]
        assert count == ticket_count

        # 3. Assert append-only trigger rejects UPDATE
        with pytest.raises(sqlite3.IntegrityError, match="decision_log is append-only"):
            cursor.execute("UPDATE decision_log SET final_disposition = 'MUTATED' WHERE run_id = ?", (run_id,))

        # 4. Assert append-only trigger rejects DELETE
        with pytest.raises(sqlite3.IntegrityError, match="decision_log is append-only"):
            cursor.execute("DELETE FROM decision_log WHERE run_id = ?", (run_id,))

        # Verify indices exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_decision_log%'")
        indexes = {row[0] for row in cursor.fetchall()}
        assert "idx_decision_log_ticket" in indexes
        assert "idx_decision_log_run" in indexes

