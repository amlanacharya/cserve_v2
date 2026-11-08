# Source Packages & REST Service

## Overview
The `src` directory hosts the core Python application modules of the CloudServe Support Orchestrator, alongside the top-level FastAPI web service in `api.py` which exposes HTTP endpoints for ticket processing, real-time decision inspection, tamper demonstration, and dashboard serving.

## Interface
- `[src/api.py:app]`: FastAPI application instance configured with OpenAPI metadata.
- `[src/api.py:orchestrator]`: Module-level `SupportOrchestrator` pipeline instance.
- `[src/api.py:get_dashboard]`: `GET /` and `GET /dashboard` endpoints returning interactive monitoring UI.
- `[src/api.py:health_check]`: `GET /health` endpoint returning `{"status": "ok"}`.
- `[src/api.py:process_ticket_endpoint]`: `POST /tickets/process` ingesting raw JSON tickets and returning `ProcessedTicketResult`.
- `[src/api.py:get_recent_decisions]`: `GET /api/decisions/recent` querying recent audit log records.
- `[src/api.py:test_database_tamper]`: `POST /api/test/tamper` demonstrating trigger abort on illegal database mutation.

### Subsystem Contracts
- [Audit Component](./audit/README.md): Persistent SQLite WAL decision log and append-only immutability triggers.
- [Classify Component](./classify/README.md): Intent, urgency, confidence scoring, and safety veto detection.
- [Core Component](./core/README.md): Domain schemas, environment settings, literal types, and regex patterns.
- [Generation Component](./generation/README.md): Resilient 3-tier cascade and XML-grounded prompt compilation.
- [Guardrails Component](./guardrails/README.md): Inbound/outbound PII scrubbing and lexical unigram entailment verification.
- [Ingest Component](./ingest/README.md): Multi-channel ticket normalization and PII redaction counting.
- [Orchestrator Component](./orchestrator/README.md): LangGraph state machine with fault-tolerant `@safe_node` containment.
- [Retrieval Component](./retrieval/README.md): Semantic Markdown chunking and ChromaDB dense vector store.
- [Routing Component](./routing/README.md): Orthogonal dual-gate routing logic and escalation packet compilation.

## Invariants
- `[src/api.py:process_ticket_endpoint]`: `raw_ticket` must be a non-empty dictionary; returns HTTP 400 if invalid or empty.
- `[src/api.py:process_ticket_endpoint]`: Uncaught processing failures are returned as HTTP 500 error responses.
- `[src/api.py:test_database_tamper]`: Requires initialized SQLite database; raises HTTP 404 if file does not exist.
- `[src/api.py:get_dashboard]`: Serves embedded fallback HTML string if `dashboard.html` template file is absent.

## Side Effects
- `[src/__init__.py:setattr]`: Applies runtime compatibility shim for Pydantic v1 `BaseSettings` on import.
- `[src/api.py:orchestrator]`: Initializes the complete LangGraph orchestrator and embedding clients at module load time.
- `[src/api.py:process_ticket_endpoint]`: Invokes full graph execution, triggering downstream vector queries, remote LLM inference, and SQLite disk writes.
- `[src/api.py:get_recent_decisions]`: Reads rows from the SQLite database at `decision_log_path`.
- `[src/api.py:test_database_tamper]`: Attempts `UPDATE` on the `decision_log` table in SQLite to test trigger protection.

## Verification
- Run: `pytest tests/integration/test_orchestrator.py -v`

