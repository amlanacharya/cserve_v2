import csv
import json
import math
from pathlib import Path
from typing import Any
import numpy as np
from src.audit.logger import get_decision_history


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


def compute_metrics(
    run_id: str,
    db_path: str | Path | None = None,
    input_tickets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Computes volume, business, technical, and governance metrics for a batch run.
    Reconciles decisions recorded in SQLite decision_log.
    """
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

            # Retrieval precision evaluation
            expected_docs = labels.get("expected_doc_ids", [])
            if expected_docs:
                retrieval_eval_count += 1
                citations_raw = r.get("citations") or "[]"
                try:
                    cites = json.loads(citations_raw) if isinstance(citations_raw, str) else citations_raw
                except Exception:
                    cites = []
                # Per-ticket precision: fraction of retrieved (cited) docs that were expected.
                # Independent of the routing score gate.
                unique_cites = set(cites)
                if unique_cites:
                    retrieval_hits += len(unique_cites & set(expected_docs)) / len(unique_cites)

    overall_accuracy = round(sum(accuracies) / len(accuracies), 4) if accuracies else None
    ece = compute_ece(confidences, accuracies, num_bins=10) if accuracies else None
    retrieval_precision = (
        round(retrieval_hits / retrieval_eval_count, 4) if retrieval_eval_count > 0 else None
    )

    # Governance Metrics
    provider_distribution: dict[str, int] = {}
    for r in history:
        p = r.get("provider_used", "unknown")
        provider_distribution[p] = provider_distribution.get(p, 0) + 1

    guardrail_trips = sum(1 for r in history if r["guardrail_status"] == "TRIPPED")
    degraded_count = sum(1 for r in history if r["is_degraded"] == 1)

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

