import json
import pytest
from evaluation.harness import run_batch_evaluation
from src.audit import logger as audit_logger
from src.orchestrator import SupportOrchestrator

TICKET = {
    "channel": "chat",
    "ticket_id": "AUD-PATH-01",
    "message": "URGENT: Entire production database is down! Disaster outage!",
}


def test_harness_db_path_controls_where_audit_rows_are_written(tmp_path):
    tickets = tmp_path / "t.json"
    tickets.write_text(json.dumps([TICKET]), encoding="utf-8")
    custom_db = tmp_path / "custom" / "custom.db"

    report = run_batch_evaluation(
        tickets, tmp_path / "out" / "report.json", delay=0, db_path=custom_db
    )

    assert custom_db.exists()
    assert report["volume"]["total_tickets"] == 1


def test_audit_write_failure_degrades_and_writes_stderr(monkeypatch, capsys):
    def boom(self, record):
        raise RuntimeError("disk full")

    monkeypatch.setattr(audit_logger.AuditLogger, "log_decision", boom)

    result = SupportOrchestrator().process_ticket(TICKET, run_id="AUD-FAIL")

    assert result.is_degraded is True
    assert "disk full" in capsys.readouterr().err
