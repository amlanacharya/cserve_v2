from evaluation.metrics import compute_metrics, export_metrics_csv
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


def _with_retrieved(rec, doc_ids):
    rec["retrieved_doc_ids"] = doc_ids
    return rec


def test_precision_at_k_ignores_routing_gate_score(tmp_path):
    records = [
        # retrieved 2, 1 expected hit -> 0.5; high score must not inflate
        _with_retrieved(_record("T1", "x", 0.9, [], top_score=0.99), ["DOC-A", "DOC-B"]),
        # retrieved nothing relevant, score high -> 0.0
        _with_retrieved(_record("T2", "x", 0.9, [], top_score=0.99), ["DOC-Z"]),
        # retrieved exactly the expected -> 1.0
        _with_retrieved(_record("T3", "x", 0.9, [], top_score=0.1), ["DOC-C"]),
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
        [_with_retrieved(_record("T1", "x", 0.9, [], top_score=0.99), [])],
        [_truth("T1", "x", ["DOC-A"])],
    )
    assert tech["retrieval_precision_at_k"] == 0.0


def _gov_record(tid, provider, status, disposition, violations, intent="x", conf=0.9, latency=10.0):
    r = _record(tid, intent, conf, [])
    r.update(
        provider_used=provider,
        guardrail_status=status,
        final_disposition=disposition,
        guardrail_violations=violations,
        latency_ms=latency,
    )
    return r


def _gov_report(tmp_path):
    db = tmp_path / "g.db"
    audit = AuditLogger(db)
    records = [
        _gov_record("G1", "groq", "PASSED", "AUTO_RESOLVED", [], conf=0.9, latency=100.0),
        _gov_record("G2", "groq", "TRIPPED", "ESCALATED_GUARDRAIL", ["PII_EMAIL_DETECTED"], conf=0.8, latency=300.0),
        _gov_record(
            "G3", "offline_mock", "TRIPPED", "ESCALATED_GUARDRAIL",
            ["HALLUCINATED_DOC_ID: KB-9 not in retrieved context"], intent="y", conf=0.6, latency=20.0,
        ),
        _gov_record("G4", "offline_mock", "PASSED", "AUTO_RESOLVED", [], conf=0.7, latency=40.0),
    ]
    for r in records:
        audit.log_decision(r)
    truths = [_truth("G1", "x", []), _truth("G2", "x", []), _truth("G3", "x", []), _truth("G4", "x", [])]
    return compute_metrics("RUN-M", db_path=db, input_tickets=truths)


def test_governance_pii_and_hallucination_rates(tmp_path):
    gov = _gov_report(tmp_path)["governance"]
    assert gov["pii_detection_rate"] == 0.25
    assert gov["pii_detected_count"] == 1
    assert gov["hallucination_suppression_rate"] == 0.25
    assert gov["hallucination_suppressed_count"] == 1


def test_governance_per_provider_breakdown(tmp_path):
    per = _gov_report(tmp_path)["governance"]["per_provider"]
    assert per["groq"]["tickets"] == 2
    assert per["groq"]["accuracy"] == 1.0
    assert per["groq"]["escalation_rate"] == 0.5
    assert per["groq"]["latency_avg_ms"] == 200.0
    assert per["groq"]["latency_p95_ms"] == 290.0
    # both correct: |1-0.9| and |1-0.8| in separate bins -> (0.1+0.2)/2
    assert per["groq"]["expected_calibration_error"] == 0.15
    assert per["offline_mock"]["accuracy"] == 0.5
    assert per["offline_mock"]["escalation_rate"] == 0.5
    assert per["offline_mock"]["latency_avg_ms"] == 30.0


def test_governance_fields_reach_csv(tmp_path):
    report = _gov_report(tmp_path)
    out = tmp_path / "metrics_summary.csv"
    export_metrics_csv(report, out)
    text = out.read_text(encoding="utf-8")
    assert "governance_pii_detection_rate,0.25" in text
    assert "governance_hallucination_suppression_rate,0.25" in text
    assert "governance_per_provider_groq_latency_avg_ms,200.0" in text
    assert "governance_per_provider_groq_expected_calibration_error,0.15" in text


def test_legacy_db_without_violations_column_is_migrated(tmp_path):
    import sqlite3

    db = tmp_path / "old.db"
    AuditLogger(db)
    conn = sqlite3.connect(str(db))
    conn.execute("ALTER TABLE decision_log DROP COLUMN guardrail_violations")
    conn.commit()
    conn.close()
    AuditLogger(db).log_decision(
        _gov_record("L1", "groq", "TRIPPED", "ESCALATED_GUARDRAIL", ["PII_EMAIL_DETECTED"])
    )
    cols = [r[1] for r in sqlite3.connect(str(db)).execute("PRAGMA table_info(decision_log)")]
    assert "guardrail_violations" in cols


# --- Issue #16: retrieval-based precision@k, classification provider, inbound PII ---


def _retrieved(tid, doc_ids, citations=()):
    r = _record(tid, "x", 0.9, list(citations))
    r["retrieved_doc_ids"] = doc_ids
    return r


def test_precision_at_k_uses_retrieved_topk_not_citations(tmp_path):
    db = tmp_path / "p.db"
    audit = AuditLogger(db)
    for r in [
        _retrieved("T1", ["A", "A", "X"]),  # 2 of 3 retrieved chunks are expected -> 2/3
        _retrieved("T2", ["Z", "Q", "Y"]),  # 1/3
        _retrieved("T3", []),  # nothing retrieved -> 0
        _retrieved("T4", ["X", "Y", "Z", "A"]),  # A is rank 4, outside k=3 -> 0
        _record("T5", "x", 0.9, ["A"]),  # legacy row, no retrieval log -> excluded
    ]:
        audit.log_decision(r)
    truths = [_truth(t, "x", d) for t, d in
              [("T1", ["A"]), ("T2", ["Q"]), ("T3", ["C"]), ("T4", ["A"]), ("T5", ["A"])]]
    tech = compute_metrics("RUN-M", db_path=db, input_tickets=truths, k=3)["technical"]
    # (2/3 + 1/3 + 0 + 0) / 4 = 0.25 ; citations (escalated rows carry none) play no part
    assert tech["retrieval_precision_at_k"] == 0.25
    assert tech["retrieval_k"] == 3


def test_precision_at_k_defaults_k_to_pipeline_top_k(tmp_path):
    from src.core.config import get_settings
    db = tmp_path / "pk.db"
    AuditLogger(db).log_decision(_retrieved("T1", ["A"]))
    tech = compute_metrics("RUN-M", db_path=db, input_tickets=[_truth("T1", "x", ["A"])])["technical"]
    assert tech["retrieval_k"] == get_settings().top_k_passages


def test_per_provider_attributed_to_classification_provider(tmp_path):
    db = tmp_path / "cp.db"
    audit = AuditLogger(db)
    a = _record("C1", "x", 0.9, [])  # classified by groq, generated by groq
    a.update(classification_provider="groq", provider_used="groq")
    b = _record("C2", "wrong", 0.8, [])  # classified by groq, generation fell back to offline
    b.update(classification_provider="groq", provider_used="offline_mock")
    c = _record("C3", "x", 0.7, [])  # legacy row: no classification_provider -> provider_used
    c.update(provider_used="gemini")
    for r in (a, b, c):
        audit.log_decision(r)
    truths = [_truth(t, "x", []) for t in ("C1", "C2", "C3")]
    gov = compute_metrics("RUN-M", db_path=db, input_tickets=truths)["governance"]
    per = gov["per_provider"]
    assert set(per) == {"groq", "gemini"}
    assert per["groq"]["tickets"] == 2
    assert per["groq"]["accuracy"] == 0.5
    # |1-0.9| = 0.1 and |0-0.8| = 0.8 in separate bins -> 0.45
    assert per["groq"]["expected_calibration_error"] == 0.45
    assert per["gemini"]["tickets"] == 1
    # generation-side distribution still keyed on provider_used
    assert gov["provider_distribution"] == {"groq": 1, "offline_mock": 1, "gemini": 1}


def test_pii_detection_counts_inbound_redactions(tmp_path):
    db = tmp_path / "pii.db"
    audit = AuditLogger(db)

    def rec(tid, redactions, violations):
        r = _gov_record(tid, "groq", "PASSED", "AUTO_RESOLVED", violations)
        r["pii_redactions_count"] = redactions
        return r

    for r in [
        rec("P1", 2, []),  # inbound only
        rec("P2", 0, ["PII_EMAIL_DETECTED"]),  # output only
        rec("P3", 1, ["CREDENTIAL_API_KEY"]),  # both: counted once
        rec("P4", 0, []),  # clean
    ]:
        audit.log_decision(r)
    gov = compute_metrics("RUN-M", db_path=db, input_tickets=[])["governance"]
    assert gov["pii_detected_count"] == 3
    assert gov["pii_detection_rate"] == 0.75
    assert gov["pii_inbound_redacted_count"] == 2
    assert gov["pii_output_violation_count"] == 2
    assert gov["pii_redactions_total"] == 3


def test_legacy_db_without_issue16_columns_is_migrated(tmp_path):
    import sqlite3

    db = tmp_path / "old16.db"
    AuditLogger(db).log_decision(_record("L1", "x", 0.9, []))
    conn = sqlite3.connect(str(db))
    for col in ("retrieved_doc_ids", "classification_provider", "pii_redactions_count"):
        conn.execute(f"ALTER TABLE decision_log DROP COLUMN {col}")
    conn.commit()
    conn.close()
    audit = AuditLogger(db)
    new = _record("L2", "x", 0.9, [])
    new.update(retrieved_doc_ids=["DOC-A"], classification_provider="groq", pii_redactions_count=2)
    audit.log_decision(new)
    rows = {r["ticket_id"]: r for r in audit.get_decision_history()}
    assert rows["L1"]["retrieved_doc_ids"] is None
    assert rows["L1"]["classification_provider"] is None
    assert rows["L1"]["pii_redactions_count"] == 0
    assert rows["L2"]["retrieved_doc_ids"] == '["DOC-A"]'
    assert rows["L2"]["classification_provider"] == "groq"
    assert rows["L2"]["pii_redactions_count"] == 2
