# Evaluation Component

## Overview
The `evaluation` package provides batch processing CLI harnesses and quantitative performance assessment tools for the CloudServe Support Orchestrator. It computes business metrics (First-Contact Resolution rate, escalation rate), technical performance (P50/P90/P99 latency, expected calibration error, retrieval precision@k), and governance compliance.

## Interface
- `[evaluation/harness.py:run_batch_evaluation]`: `run_batch_evaluation(input_path: str | Path, output_path: str | Path, delay: float = 1.5, db_path: str | Path | None = None) -> dict` executes unattended evaluation across datasets.
- `[evaluation/harness.py:main]`: `main() -> None` CLI entrypoint parsing `--input`, `--output`, `--delay`, and `--db`.
- `[evaluation/metrics.py:compute_metrics]`: `compute_metrics(run_id: str, db_path: str | Path | None = None, input_tickets: list[dict[str, Any]] | None = None, k: int | None = None) -> dict[str, Any]` evaluates comprehensive statistics from the SQLite decision log.
- `[evaluation/metrics.py:compute_ece]`: `compute_ece(confidences: list[float], accuracies: list[int], num_bins: int = 10) -> float` computes 10-bin Expected Calibration Error for confidence calibration.
- `[evaluation/metrics.py:export_metrics_csv]`: `export_metrics_csv(report: dict[str, Any], output_path: str | Path) -> None` flattens report metrics into a tabular CSV file.

## Invariants
- `[evaluation/harness.py:run_batch_evaluation]`: Input file must exist on disk and contain a JSON array of tickets; logs error and exits with code 1 if violated.
- `[evaluation/metrics.py:compute_metrics]`: Returns early with status `'NO_RECORDS_FOUND'` if zero audit rows are found for the provided `run_id`.
- `[evaluation/metrics.py:compute_metrics]`: Business metric `fcr_target_met` evaluates `True` if and only if `fcr_rate >= 0.65`.
- `[evaluation/metrics.py:compute_ece]`: Returns `0.0` if input arrays are empty or lengths diverge.

## Side Effects
- `[evaluation/harness.py:run_batch_evaluation]`: Invokes `SupportOrchestrator.process_ticket`, executing the full graph pipeline and inserting audit rows into SQLite.
- `[evaluation/harness.py:run_batch_evaluation]`: Writes JSON evaluation report to `output_path` and tabular summary to `metrics_summary.csv`.
- `[evaluation/harness.py:run_batch_evaluation]`: Sleeps `time.sleep(delay)` between successive tickets to avoid upstream provider throttling.

## Verification
- Run: `python -m evaluation.harness --input 05_Datasets/validation_tickets.json --output evaluation/validation_report.json --delay 0.1`

