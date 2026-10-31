import argparse
import json
import logging
import sys
import time
import uuid
from pathlib import Path
from tqdm import tqdm
from evaluation.metrics import compute_metrics, export_metrics_csv
from src.core.config import get_settings
from src.orchestrator import SupportOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_batch_evaluation(
    input_path: str | Path,
    output_path: str | Path,
    delay: float = 1.5,
    db_path: str | Path | None = None,
) -> dict:
    in_file = Path(input_path)
    if not in_file.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    with open(in_file, "r", encoding="utf-8") as f:
        tickets = json.load(f)

    if not isinstance(tickets, list):
        logger.error(f"Expected a JSON list of tickets, got {type(tickets)}")
        sys.exit(1)

    run_id = f"batch_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    logger.info(f"Starting batch evaluation run {run_id} ({len(tickets)} tickets, delay={delay}s)")

    orchestrator = SupportOrchestrator(db_path=db_path)

    for idx, raw_ticket in enumerate(tqdm(tickets, desc="Processing Evaluation Tickets")):
        try:
            orchestrator.process_ticket(raw_ticket, run_id=run_id)
        except Exception as e:
            logger.error(f"Unexpected error processing ticket {raw_ticket.get('ticket_id')}: {e}")

        if delay > 0 and idx < len(tickets) - 1:
            time.sleep(delay)

    logger.info(f"Batch processing completed for run {run_id}. Computing metrics...")
    metrics_report = compute_metrics(
        run_id=run_id,
        db_path=db_path,
        input_tickets=tickets,
    )

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics_report, f, indent=2)

    csv_path = out_file.parent / "metrics_summary.csv"
    export_metrics_csv(metrics_report, csv_path)

    logger.info(f"Metrics report written to: {out_file}")
    logger.info(f"CSV summary written to: {csv_path}")

    # Print summary to console
    print("\n" + "=" * 60)
    print("           CLOUDFORCE / CLOUDSERVE EVALUATION REPORT           ")
    print("=" * 60)
    print(f"Run ID: {run_id}")
    vol = metrics_report.get("volume", {})
    biz = metrics_report.get("business", {})
    tech = metrics_report.get("technical", {})
    gov = metrics_report.get("governance", {})

    print(f"Total Processed: {vol.get('total_tickets')}")
    print(f"Auto-Resolved:   {vol.get('auto_resolved')} ({vol.get('auto_resolve_rate', 0)*100:.1f}%)")
    print(f"Escalated:       {vol.get('total_escalated')} ({vol.get('escalation_rate', 0)*100:.1f}%)")
    print(f"  - Router:      {vol.get('escalated_router')}")
    print(f"  - Guardrail:   {vol.get('escalated_guardrail')}")
    print(f"  - Error:       {vol.get('escalated_error')}")
    print("-" * 60)
    print(f"FCR Rate:        {biz.get('first_contact_resolution_rate', 0)*100:.1f}% (Target >= 65%: {biz.get('fcr_target_met')})")
    print(f"Accuracy:        {tech.get('accuracy')}")
    print(f"ECE (Calib):     {tech.get('expected_calibration_error')}")
    print(f"Latency P95:     {tech.get('latency_p95_ms')} ms")
    print(f"Guardrail Trips: {gov.get('guardrail_tripped_count')}")
    print(f"Provider Mix:    {gov.get('provider_distribution')}")
    print("=" * 60 + "\n")

    return metrics_report


def main():
    settings = get_settings()
    parser = argparse.ArgumentParser(description="CloudServe Support Orchestrator Batch Evaluation CLI")
    parser.add_argument(
        "--input",
        type=str,
        default="05_Datasets/validation_tickets.json",
        help="Path to inbound ticket dataset JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation/validation_report.json",
        help="Path for validation report JSON output",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=settings.batch_delay,
        help="Inter-ticket delay in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=settings.decision_log_path,
        help="SQLite database path",
    )

    args = parser.parse_args()
    run_batch_evaluation(
        input_path=args.input,
        output_path=args.output,
        delay=args.delay,
        db_path=args.db_path,
    )


if __name__ == "__main__":
    main()

