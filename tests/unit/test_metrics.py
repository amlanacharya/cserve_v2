from evaluation.metrics import compute_metrics
from src.audit.logger import AuditLogger


def _record(tid, intent, conf, citations, top_score=0.9):
    return {
        "run_id": "RUN-M",
        "ticket_id": tid,
        "channel": "email",
        "inferred_intent": intent,
        "intent_confidence": conf,
        "urgency": "LOW",
        "top_retrieval_score": top_score,
        "routing_action": "AUTO_RESPOND",
        "routing_reason": "ok",
        "guardrail_status": "PASSED",
        "final_disposition": "AUTO_RESOLVED",
        "citations": citations,
        "provider_used": "offline_mock",
        "is_degraded": False,
        "latency_ms": 10.0,
    }


def _truth(tid, intent, docs):
    return {"ticket_id": tid, "labels": {"intent": intent, "expected_doc_ids": docs}}


def _run(tmp_path, records, truths):
    db = tmp_path / "m.db"
    audit = AuditLogger(db)
    for r in records:
        audit.log_decision(r)
    return compute_metrics("RUN-M", db_path=db, input_tickets=truths)["technical"]


def test_intent_accuracy_is_exact_match_not_substring(tmp_path):
    records = [
        _record("T1", "auth", 0.8, []),
        _record("T2", "api_key_issue", 0.6, []),
    ]
    truths = [_truth("T1", "authentication", []), _truth("T2", "api_key_issue", [])]
    tech = _run(tmp_path, records, truths)
    # T1: "auth" != "authentication" (wrong); T2 right -> 1/2
    assert tech["accuracy"] == 0.5
    # bins: 0.8 conf acc 0 -> |0-0.8|; 0.6 conf acc 1 -> |1-0.6|; ECE=(0.8+0.4)/2
    assert tech["expected_calibration_error"] == 0.6


def test_precision_at_k_ignores_routing_gate_score(tmp_path):
    records = [
        # cited 2, 1 expected hit -> 0.5; high score must not inflate
        _record("T1", "x", 0.9, ["DOC-A", "DOC-B"], top_score=0.99),
        # cited nothing relevant, score high -> 0.0
        _record("T2", "x", 0.9, ["DOC-Z"], top_score=0.99),
        # cited exactly the expected -> 1.0
        _record("T3", "x", 0.9, ["DOC-C"], top_score=0.1),
    ]
    truths = [
        _truth("T1", "x", ["DOC-A"]),
        _truth("T2", "x", ["DOC-Q"]),
        _truth("T3", "x", ["DOC-C"]),
    ]
    tech = _run(tmp_path, records, truths)
    # (0.5 + 0 + 1) / 3 = 0.5
    assert tech["retrieval_precision_at_k"] == 0.5


def test_precision_at_k_zero_when_nothing_retrieved(tmp_path):
    tech = _run(
        tmp_path,
        [_record("T1", "x", 0.9, [], top_score=0.99)],
        [_truth("T1", "x", ["DOC-A"])],
    )
    assert tech["retrieval_precision_at_k"] == 0.0
