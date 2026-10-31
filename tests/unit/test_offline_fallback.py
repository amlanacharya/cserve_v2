import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import patch

from src.classify.cache import compute_ticket_hash
from src.classify.classifier import classify_ticket
from src.core.models import CanonicalTicket
from src.orchestrator.wrappers import safe_node
from src.routing.router import evaluate_route

OFFLINE_REASON = "OFFLINE_FALLBACK: all network providers unavailable"
FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _ticket(**kw):
    base = dict(ticket_id="OFF-1", channel="chat", body="please help with login", created_at=FIXED)
    base.update(kw)
    return CanonicalTicket(**base)


def _live_json():
    return json.dumps(
        {"inferred_intent": "auth_issue", "intent_alternatives": {}, "urgency": "LOW", "confidence": 0.9}
    )


def test_route_reason_reports_offline_fallback():
    action, reason = evaluate_route(0.9, 0.9, "LOW", True, provider_used="offline_mock")
    assert action == "ESCALATE"
    assert OFFLINE_REASON in reason


def test_route_reason_unchanged_for_live_provider():
    _, reason = evaluate_route(0.9, 0.9, "LOW", False, provider_used="groq")
    assert "OFFLINE_FALLBACK" not in reason


def test_offline_result_not_cached_and_reclassified_after_recovery(isolated_classification_cache):
    ticket = _ticket()
    with patch("src.classify.classifier.call_cascade", return_value=("{}", "offline_mock")):
        first = classify_ticket(ticket)
    assert first["provider_used"] == "offline_mock"
    with patch("src.classify.classifier.call_cascade", return_value=(_live_json(), "groq")):
        second = classify_ticket(ticket)
    assert second["provider_used"] == "groq"


def test_live_result_is_cached(isolated_classification_cache):
    ticket = _ticket()
    with patch("src.classify.classifier.call_cascade", return_value=(_live_json(), "groq")) as m:
        classify_ticket(ticket)
        classify_ticket(ticket)
    assert m.call_count == 1


def test_cache_key_is_sha256_of_canonical_ticket_json():
    ticket = _ticket(sender_ref="u1", metadata={"k": "v"})
    expected = hashlib.sha256(
        json.dumps(ticket.model_dump(mode="json"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    assert compute_ticket_hash(ticket) == expected
    assert compute_ticket_hash(ticket) != compute_ticket_hash(_ticket(sender_ref="u2", metadata={"k": "v"}))


def test_normalize_fallback_preserves_channel():
    @safe_node(node_name="normalize_node")
    def boom(state):
        raise RuntimeError("x")

    out = boom({"raw_ticket": {"ticket_id": "T", "channel": "Forum", "body": "b"}})
    assert out["canonical_ticket"].channel == "forum"
    out = boom({"raw_ticket": {"ticket_id": "T", "channel": "bogus", "body": "b"}})
    assert out["canonical_ticket"].channel == "email"


def test_route_reason_names_node_failure_not_offline_fallback():
    action, reason = evaluate_route(
        0.0, 0.9, "HIGH", True, provider_used="offline_mock", node_failure="classify_node"
    )
    assert action == "ESCALATE"
    assert "NODE_FAILURE: classify_node" in reason
    assert "OFFLINE_FALLBACK" not in reason


def test_classify_crash_reports_node_failure_end_to_end(monkeypatch):
    from src.orchestrator import SupportOrchestrator, nodes

    def boom(_ticket):
        raise RuntimeError("simulated classify crash")

    monkeypatch.setattr(nodes, "classify_ticket", boom)
    result = SupportOrchestrator().process_ticket(
        {"channel": "chat", "ticket_id": "NF-1", "message": "help me"}, run_id="RUN-NF-1"
    )
    assert result.is_degraded is True
    assert "NODE_FAILURE: classify_node" in result.routing_reason
    assert "OFFLINE_FALLBACK" not in result.routing_reason


def test_genuine_offline_still_reports_offline_fallback_end_to_end(monkeypatch):
    from src.orchestrator import SupportOrchestrator

    result = SupportOrchestrator().process_ticket(
        {"channel": "chat", "ticket_id": "OFF-E2E", "message": "help me"}, run_id="RUN-OFF-E2E"
    )
    assert OFFLINE_REASON in result.routing_reason


def test_normalize_crash_fallback_redacts_body_and_counts_redactions():
    @safe_node(node_name="normalize_node")
    def boom(state):
        raise RuntimeError("x")

    out = boom({"raw_ticket": {"ticket_id": "T", "channel": "email", "body": "mail me at bob@example.com"}})
    assert "bob@example.com" not in out["canonical_ticket"].body
    assert out["pii_redactions_count"] == 1
