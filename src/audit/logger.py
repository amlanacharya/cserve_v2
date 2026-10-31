import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from src.core.config import get_settings

logger = logging.getLogger(__name__)

DDL_STATEMENTS = """
CREATE TABLE IF NOT EXISTS decision_log (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                TEXT    NOT NULL,
    ticket_id             TEXT    NOT NULL,
    channel               TEXT    NOT NULL CHECK (channel IN ('email','chat','docs_comment','forum')),
    logged_at             TEXT    NOT NULL,
    inferred_intent       TEXT    NOT NULL,
    intent_confidence     REAL    NOT NULL CHECK (intent_confidence BETWEEN 0 AND 1),
    intent_alternatives   TEXT    NOT NULL DEFAULT '{}',
    urgency               TEXT    NOT NULL CHECK (urgency IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    top_retrieval_score   REAL    NOT NULL CHECK (top_retrieval_score BETWEEN 0 AND 1),
    must_not_auto_respond INTEGER NOT NULL CHECK (must_not_auto_respond IN (0,1)),
    routing_action        TEXT    NOT NULL CHECK (routing_action IN ('AUTO_RESPOND','ESCALATE')),
    routing_reason        TEXT    NOT NULL,
    guardrail_status      TEXT             CHECK (guardrail_status IS NULL OR guardrail_status IN ('PASSED','TRIPPED')),
    final_disposition     TEXT    NOT NULL CHECK (final_disposition IN
                              ('AUTO_RESOLVED','ESCALATED_ROUTER','ESCALATED_GUARDRAIL','ESCALATED_ERROR')),
    citations             TEXT    NOT NULL DEFAULT '[]',
    provider_used         TEXT    NOT NULL CHECK (provider_used IN ('groq','gemini','offline_mock')),
    is_degraded           INTEGER NOT NULL CHECK (is_degraded IN (0,1)),
    error_details         TEXT,
    guardrail_violations  TEXT    NOT NULL DEFAULT '[]',
    latency_ms           REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decision_log_ticket ON decision_log (ticket_id);
CREATE INDEX IF NOT EXISTS idx_decision_log_run    ON decision_log (run_id);

CREATE TRIGGER IF NOT EXISTS decision_log_no_update BEFORE UPDATE ON decision_log
BEGIN SELECT RAISE(ABORT, 'decision_log is append-only'); END;

CREATE TRIGGER IF NOT EXISTS decision_log_no_delete BEFORE DELETE ON decision_log
BEGIN SELECT RAISE(ABORT, 'decision_log is append-only'); END;
"""

_DB_LOCK = threading.Lock()


class AuditLogger:
    def __init__(self, db_path: str | Path | None = None):
        settings = get_settings()
        self.db_path = Path(db_path or settings.decision_log_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self) -> None:
        with _DB_LOCK:
            with self._get_connection() as conn:
                conn.executescript(DDL_STATEMENTS)
                existing = {r[1] for r in conn.execute("PRAGMA table_info(decision_log)")}
                if "guardrail_violations" not in existing:
                    conn.execute(
                        "ALTER TABLE decision_log ADD COLUMN guardrail_violations TEXT NOT NULL DEFAULT '[]'"
                    )
                conn.commit()

    def log_decision(self, record: dict[str, Any]) -> None:
        """
        Appends a processed ticket record to the decision_log table.
        Retries once if locked or temporary error occurs.
        """
        logged_at = record.get("logged_at") or datetime.now(timezone.utc).isoformat()
        intent_alternatives = record.get("intent_alternatives", "{}")
        if isinstance(intent_alternatives, dict):
            intent_alternatives = json.dumps(intent_alternatives)

        citations = record.get("citations", "[]")
        if isinstance(citations, list):
            citations = json.dumps(citations)

        violations = record.get("guardrail_violations") or []
        if not isinstance(violations, str):
            violations = json.dumps(list(violations))

        sql = """
        INSERT INTO decision_log (
            run_id, ticket_id, channel, logged_at, inferred_intent,
            intent_confidence, intent_alternatives, urgency, top_retrieval_score,
            must_not_auto_respond, routing_action, routing_reason, guardrail_status,
            final_disposition, citations, provider_used, is_degraded, error_details,
            guardrail_violations, latency_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            str(record["run_id"]),
            str(record["ticket_id"]),
            str(record["channel"]).lower(),
            str(logged_at),
            str(record["inferred_intent"]),
            float(record["intent_confidence"]),
            intent_alternatives,
            str(record["urgency"]).upper(),
            float(record["top_retrieval_score"]),
            1 if record.get("must_not_auto_respond") else 0,
            str(record["routing_action"]),
            str(record["routing_reason"]),
            str(record["guardrail_status"]) if record.get("guardrail_status") else None,
            str(record["final_disposition"]),
            citations,
            str(record["provider_used"]),
            1 if record.get("is_degraded") else 0,
            str(record.get("error_details")) if record.get("error_details") else None,
            violations,
            float(record.get("latency_ms", 0.0)),
        )

        for attempt in range(2):
            try:
                with _DB_LOCK:
                    with self._get_connection() as conn:
                        conn.execute(sql, params)
                        conn.commit()
                return
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"Audit log write failed, retrying: {e}")
                    continue
                logger.error(f"Audit log critical write failure: {e}", exc_info=True)
                raise

    def get_decision_history(
        self,
        run_id: str | None = None,
        ticket_id: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM decision_log WHERE 1=1"
        params: list[Any] = []
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        if ticket_id:
            query += " AND ticket_id = ?"
            params.append(ticket_id)
        query += " ORDER BY id ASC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]


_GLOBAL_AUDIT_LOGGER: AuditLogger | None = None


def get_audit_logger(db_path: str | Path | None = None) -> AuditLogger:
    global _GLOBAL_AUDIT_LOGGER
    if db_path is not None:
        return AuditLogger(db_path)
    if _GLOBAL_AUDIT_LOGGER is None:
        _GLOBAL_AUDIT_LOGGER = AuditLogger()
    return _GLOBAL_AUDIT_LOGGER


def log_decision(record: dict[str, Any], db_path: str | Path | None = None) -> None:
    logger_inst = get_audit_logger(db_path)
    logger_inst.log_decision(record)


def get_decision_history(
    run_id: str | None = None,
    ticket_id: str | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    logger_inst = get_audit_logger(db_path)
    return logger_inst.get_decision_history(run_id=run_id, ticket_id=ticket_id)

