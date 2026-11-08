# Audit Component

## Overview
The `audit` package provides persistent, tamper-evident audit logging for the CloudServe Support Orchestrator. It records 100% of pipeline decisions into an append-only SQLite store configured with Write-Ahead Logging (WAL) and database-level immutability triggers.

## Interface
- `[src/audit/logger.py:AuditLogger]`: Class managing the SQLite connection pool, schema initialization, migrations, and write operations.
- `[src/audit/logger.py:get_audit_logger]`: `get_audit_logger(db_path: str | Path | None = None) -> AuditLogger` retrieves the global singleton or initializes a custom instance.
- `[src/audit/logger.py:log_decision]`: `log_decision(record: dict[str, Any], db_path: str | Path | None = None) -> None` appends a decision log record.
- `[src/audit/logger.py:get_decision_history]`: `get_decision_history(run_id: str | None = None, ticket_id: str | None = None, db_path: str | Path | None = None) -> list[dict[str, Any]]` queries logged decisions by run or ticket identifier.

## Invariants
- `[src/audit/logger.py:DDL_STATEMENTS]`: Immutability triggers `decision_log_no_update` and `decision_log_no_delete` abort all `UPDATE` and `DELETE` queries with `'decision_log is append-only'`.
- `[src/audit/logger.py:DDL_STATEMENTS]`: Check constraints enforce valid channel values (`'email'`, `'chat'`, `'docs_comment'`, `'forum'`), normalized probability ranges (`intent_confidence BETWEEN 0 AND 1`, `top_retrieval_score BETWEEN 0 AND 1`), and routing actions (`'AUTO_RESPOND'`, `'ESCALATE'`).
- `[src/audit/logger.py:AuditLogger.log_decision]`: Database writes are protected across concurrent threads via `_DB_LOCK` with retry containment.

## Side Effects
- `[src/audit/logger.py:AuditLogger._init_db]`: Creates parent directories on disk, establishes SQLite WAL journal mode (`PRAGMA journal_mode=WAL`), executes table and index DDL, and runs additive migrations.
- `[src/audit/logger.py:AuditLogger.log_decision]`: Appends serialized records into the `decision_log` table in SQLite.

## Verification
- Run: `pytest tests/unit/test_audit.py -v`

