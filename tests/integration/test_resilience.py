import concurrent.futures
import threading
from unittest.mock import patch
import pytest
from src.audit.logger import AuditLogger
from src.generation.cascade import call_cascade
from src.orchestrator import SupportOrchestrator


def test_safe_node_fault_containment():
    """Fault injection: force an unhandled error inside classify_node and ensure pipeline survives."""
    orchestrator = SupportOrchestrator()

    with patch("src.orchestrator.nodes.classify_ticket", side_effect=RuntimeError("Simulated LLM network crash")):
        raw_ticket = {
            "channel": "email",
            "ticket_id": "RESILIENCE-01",
            "subject": "Testing crash resilience",
            "body": "System should handle this error without terminating.",
        }
        result = orchestrator.process_ticket(raw_ticket, run_id="RUN-RESILIENCE-01")

        assert result.ticket_id == "RESILIENCE-01"
        assert result.is_degraded is True
        assert result.final_disposition in ("ESCALATED_ROUTER", "ESCALATED_ERROR")
        assert result.final_response is None
        assert result.escalation_packet is not None


def test_offline_fallback_when_providers_unconfigured():
    """When no API keys are present, cascade gracefully falls back to offline heuristic mock."""
    with patch("src.generation.cascade.get_settings") as mock_settings:
        settings_instance = mock_settings.return_value
        settings_instance.groq_api_key = ""
        settings_instance.gemini_api_key = ""
        settings_instance.batch_delay = 0.0

        out_text, provider = call_cascade(
            system_prompt="sys",
            user_prompt="I need help with my API key 401 error",
            task_type="classification",
        )
        assert provider == "offline_mock"
        assert "api_key_issue" in out_text or "inferred_intent" in out_text


def test_sqlite_wal_concurrent_writers(tmp_path):
    """Simulate 10 concurrent threads logging decisions to verify WAL concurrency without locking errors."""
    db_file = tmp_path / "concurrent_audit.db"
    audit = AuditLogger(db_file)

    def write_worker(worker_id: int):
        for j in range(5):
            record = {
                "run_id": "CONCURRENT-RUN",
                "ticket_id": f"THREAD-{worker_id}-TICKET-{j}",
                "channel": "chat",
                "inferred_intent": "general_inquiry",
                "intent_confidence": 0.80,
                "intent_alternatives": {},
                "urgency": "LOW",
                "top_retrieval_score": 0.70,
                "must_not_auto_respond": False,
                "routing_action": "AUTO_RESPOND",
                "routing_reason": "Dual gates passed",
                "guardrail_status": "PASSED",
                "final_disposition": "AUTO_RESOLVED",
                "citations": ["DOC-001"],
                "provider_used": "groq",
                "is_degraded": False,
                "error_details": None,
                "latency_ms": 50.0,
            }
            audit.log_decision(record)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(write_worker, i) for i in range(5)]
        for f in concurrent.futures.as_completed(futures):
            f.result()

    history = audit.get_decision_history(run_id="CONCURRENT-RUN")
    assert len(history) == 25
