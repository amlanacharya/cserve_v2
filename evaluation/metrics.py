import csv
import json
import math
from pathlib import Path
from typing import Any
import numpy as np
from src.audit.logger import get_decision_history
from src.core.config import get_settings


def compute_ece(confidences: list[float], accuracies: list[int], num_bins: int = 10) -> float:
    """
    Computes Expected Calibration Error (ECE) across M equal-width bins in [0, 1].
    ECE = sum_{m=1}^M ( |B_m| / N ) * | acc(B_m) - conf(B_m) |
    """
    if not confidences or not accuracies or len(confidences) != len(accuracies):
        return 0.0

    n = len(confidences)
    bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
    ece = 0.0

    for i in range(num_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        # In-bin mask
        if i == num_bins - 1:
            in_bin = [
                (bin_lower <= c <= bin_upper) for c in confidences
            ]
        else:
            in_bin = [
                (bin_lower <= c < bin_upper) for c in confidences
            ]

        bin_size = sum(in_bin)
        if bin_size > 0:
            bin_acc = sum(acc for acc, match in zip(accuracies, in_bin) if match) / bin_size
            bin_conf = sum(c for c, match in zip(confidences, in_bin) if match) / bin_size
            ece += (bin_size / n) * abs(bin_acc - bin_conf)

    return round(float(ece), 4)


_PII_PREFIXES = ("PII_", "CREDENTIAL_")
_HALLUCINATION_PREFIXES = (
    "HALLUCINATED_",
    "LOW_UNIGRAM_ENTAILMENT",
    "MISSING_DOC_CITATIONS",
    "EMPTY_RETRIEVED_CONTEXT",
)


def _has_violation(row: dict[str, Any], prefixes: tuple[str, ...]) -> bool:
    raw = row.get("guardrail_violations") or "[]"
    try:
        violations = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return False
    return any(str(v).startswith(prefixes) for v in violations)


CLASSIFY_FAILED = "classify_failed"  # per-provider bucket for tickets whose classify node crashed


def _pii_redactions(row: dict[str, Any]) -> int:
    return int(row.get("pii_redactions_count") or 0)


def _classification_provider(row: dict[str, Any]) -> str:
    """Provider that classified the ticket.

    A classify crash has no provider (bucketed apart from offline_mock); legacy rows (NULL
    classification_provider, no crash) fall back to provider_used.
    """
    if row.get("failed_node") == "classify_node":
        return CLASSIFY_FAILED
    return row.get("classification_provider") or row.get("provider_used", "unknown")


def _retrieved_doc_ids(row: dict[str, Any]) -> list[str] | None:
    """Ranked doc_id of each retrieved chunk; None for legacy rows that never logged retrieval."""
    raw = row.get("retrieved_doc_ids")
    if raw is None:
        return None
    try:
        ids = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return None
    return [str(i) for i in ids]


def _provider_stats(
    rows: list[dict[str, Any]], ground_truth_map: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    n = len(rows)
    confidences: list[float] = []
    accuracies: list[int] = []
    for r in rows:
        gt = ground_truth_map.get(r["ticket_id"])
        if gt and "labels" in gt:
            true_intent = str(gt["labels"].get("intent", "")).lower().strip()
            accuracies.append(int(str(r["inferred_intent"]).lower().strip() == true_intent))
            confidences.append(float(r["intent_confidence"]))
    latencies = [float(r["latency_ms"]) for r in rows if r["latency_ms"] is not None]
    escalated = sum(1 for r in rows if r["final_disposition"] != "AUTO_RESOLVED")
    return {
        "tickets": n,
        "accuracy": round(sum(accuracies) / len(accuracies), 4) if accuracies else None,
        "expected_calibration_error": compute_ece(confidences, accuracies) if accuracies else None,
        "latency_avg_ms": round(float(np.mean(latencies)), 2) if latencies else 0.0,
        "latency_p95_ms": round(float(np.percentile(latencies, 95)), 2) if latencies else 0.0,
        "escalation_rate": round(escalated / n, 4),
    }


def compute_metrics(
    run_id: str,
    db_path: str | Path | None = None,
    input_tickets: list[dict[str, Any]] | None = None,
    k: int | None = None,
) -> dict[str, Any]:
    """
    Computes volume, business, technical, and governance metrics for a batch run.
    Reconciles decisions recorded in SQLite decision_log.

    k overrides the precision@k cut-off for every row. By default each row uses the retrieval
    top-k recorded with it (decision_log.retrieval_k), so precision@k is measured over exactly
    the chunks that were handed to generation even if TOP_K_PASSAGES changes later; legacy rows
    without a recorded k use the current setting.
    """
    default_k = get_settings().top_k_passages
    history = get_decision_history(run_id=run_id, db_path=db_path)
    total_tickets = len(history)

    if total_tickets == 0:
        return {"run_id": run_id, "total_tickets": 0, "status": "NO_RECORDS_FOUND"}

    # Map input tickets by ticket_id for ground truth reconciliation
    ground_truth_map: dict[str, dict[str, Any]] = {}
    if input_tickets:
        for t in input_tickets:
            tid = t.get("ticket_id")
            if tid:
                ground_truth_map[tid] = t

    # Volume & Business Metrics
    auto_resolved = sum(1 for r in history if r["final_disposition"] == "AUTO_RESOLVED")
    escalated_router = sum(1 for r in history if r["final_disposition"] == "ESCALATED_ROUTER")
    escalated_guardrail = sum(1 for r in history if r["final_disposition"] == "ESCALATED_GUARDRAIL")
    escalated_error = sum(1 for r in history if r["final_disposition"] == "ESCALATED_ERROR")
    total_escalated = escalated_router + escalated_guardrail + escalated_error

    fcr_rate = round(auto_resolved / total_tickets, 4)
    escalation_rate = round(total_escalated / total_tickets, 4)

    # Technical Metrics: Latency Percentiles
    latencies = [float(r["latency_ms"]) for r in history if r["latency_ms"] is not None]
    if latencies:
        latencies_sorted = sorted(latencies)
        p50_latency = round(float(np.percentile(latencies_sorted, 50)), 2)
        p90_latency = round(float(np.percentile(latencies_sorted, 90)), 2)
        p95_latency = round(float(np.percentile(latencies_sorted, 95)), 2)
        avg_latency = round(float(np.mean(latencies_sorted)), 2)
        max_latency = round(float(max(latencies_sorted)), 2)
    else:
        p50_latency = p90_latency = p95_latency = avg_latency = max_latency = 0.0

    # Technical Metrics: Classification Accuracy & ECE
    confidences: list[float] = []
    accuracies: list[int] = []
    retrieval_hits = 0
    retrieval_eval_count = 0
    ks_used: list[int] = []
    # A crashed retrieval node is a failure, not a measurement: it is reported, not scored 0.
    retrieval_failed = sum(1 for r in history if r.get("failed_node") == "retrieval_node")

    for r in history:
        tid = r["ticket_id"]
        pred_intent = str(r["inferred_intent"]).lower().strip()
        conf = float(r["intent_confidence"])

        gt_ticket = ground_truth_map.get(tid)
        if gt_ticket and "labels" in gt_ticket:
            labels = gt_ticket["labels"]
            true_intent = str(labels.get("intent", "")).lower().strip()
            is_match = int(pred_intent == true_intent)
            accuracies.append(is_match)
            confidences.append(conf)

            # Retrieval precision@k: fraction of the first k retrieved chunks whose doc is expected.
            # Uses what retrieval returned (not citations, which vanish on escalation) and is
            # independent of the routing score gate. Legacy rows without a retrieval log are skipped.
            expected_docs = labels.get("expected_doc_ids", [])
            retrieved = _retrieved_doc_ids(r)
            if expected_docs and retrieved is not None and r.get("failed_node") != "retrieval_node":
                retrieval_eval_count += 1
                row_k = k or r.get("retrieval_k") or default_k
                ks_used.append(row_k)
                top_k = retrieved[:row_k]
                if top_k:
                    expected = set(expected_docs)
                    retrieval_hits += sum(1 for d in top_k if d in expected) / len(top_k)

    overall_accuracy = round(sum(accuracies) / len(accuracies), 4) if accuracies else None
    ece = compute_ece(confidences, accuracies, num_bins=10) if accuracies else None
    retrieval_precision = (
        round(retrieval_hits / retrieval_eval_count, 4) if retrieval_eval_count > 0 else None
    )

    recorded_ks = [r["retrieval_k"] for r in history if r.get("retrieval_k")]
    reported_k = k or max(ks_used or recorded_ks or [default_k])

    # Governance Metrics
    provider_distribution: dict[str, int] = {}
    for r in history:
        p = r.get("provider_used", "unknown")
        provider_distribution[p] = provider_distribution.get(p, 0) + 1

    guardrail_trips = sum(1 for r in history if r["guardrail_status"] == "TRIPPED")
    degraded_count = sum(1 for r in history if r["is_degraded"] == 1)

    # PII detection: a ticket counts once if inbound PII was redacted at ingest OR the output
    # guardrails flagged PII/credentials.
    inbound_flags = [_pii_redactions(r) > 0 for r in history]
    output_flags = [_has_violation(r, _PII_PREFIXES) for r in history]
    pii_inbound = sum(inbound_flags)
    pii_output = sum(output_flags)
    pii_detected = sum(i or o for i, o in zip(inbound_flags, output_flags))
    pii_redactions_total = sum(_pii_redactions(r) for r in history)
    halluc_suppressed = sum(1 for r in history if _has_violation(r, _HALLUCINATION_PREFIXES))

    # Per-provider accuracy/ECE are attributed to the provider that classified the ticket,
    # not the one that generated the draft (provider_used is overwritten by generation).
    per_provider: dict[str, dict[str, Any]] = {}
    for provider in dict.fromkeys(_classification_provider(r) for r in history):
        rows = [r for r in history if _classification_provider(r) == provider]
        per_provider[provider] = _provider_stats(rows, ground_truth_map)

    report = {
        "run_id": run_id,
        "volume": {
            "total_tickets": total_tickets,
            "auto_resolved": auto_resolved,
            "total_escalated": total_escalated,
            "escalated_router": escalated_router,
            "escalated_guardrail": escalated_guardrail,
            "escalated_error": escalated_error,
            "auto_resolve_rate": fcr_rate,
            "escalation_rate": escalation_rate,
        },
        "business": {
            "first_contact_resolution_rate": fcr_rate,
            "fcr_target_met": fcr_rate >= 0.65,
        },
        "technical": {
            "accuracy": overall_accuracy,
            "expected_calibration_error": ece,
            "retrieval_precision_at_k": retrieval_precision,
            "retrieval_k": reported_k,
            "retrieval_failed_count": retrieval_failed,
            "latency_p50_ms": p50_latency,
            "latency_p90_ms": p90_latency,
            "latency_p95_ms": p95_latency,
            "latency_avg_ms": avg_latency,
            "latency_max_ms": max_latency,
        },
        "governance": {
            "guardrail_tripped_count": guardrail_trips,
            "guardrail_trip_rate": round(guardrail_trips / total_tickets, 4),
            "degraded_count": degraded_count,
            "degraded_rate": round(degraded_count / total_tickets, 4),
            "provider_distribution": provider_distribution,
            "pii_detected_count": pii_detected,
            "pii_detection_rate": round(pii_detected / total_tickets, 4),
            "pii_inbound_redacted_count": pii_inbound,
            "pii_output_violation_count": pii_output,
            "pii_redactions_total": pii_redactions_total,
            "hallucination_suppressed_count": halluc_suppressed,
            "hallucination_suppression_rate": round(halluc_suppressed / total_tickets, 4),
            "per_provider": per_provider,
        },
    }
    return report


def export_metrics_csv(report: dict[str, Any], output_path: str | Path) -> None:
    """Exports flattened metrics to a CSV file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []

    def flatten(prefix: str, d: dict[str, Any]):
        for k, v in d.items():
            col_name = f"{prefix}_{k}" if prefix else k
            if isinstance(v, dict):
                flatten(col_name, v)
            else:
                rows.append({"metric": col_name, "value": v})

    flatten("", report)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)

