# Orchestrator Component

## Overview
The `orchestrator` package manages the end-to-end lifecycle of support tickets via a LangGraph state machine. It coordinates normalization, classification, grounded vector retrieval, orthogonal routing, draft generation, guardrail evaluation, escalation packet construction, and persistent audit logging under fault-tolerant `@safe_node` exception boundaries.

## Interface
- `[src/orchestrator/graph.py:SupportOrchestrator]`: Entrypoint pipeline class providing `process_ticket(raw_ticket: dict[str, Any], run_id: str | None = None) -> ProcessedTicketResult`.
- `[src/orchestrator/graph.py:build_graph]`: Compiles the LangGraph `StateGraph` containing conditional branching edges (`route_decision`, `generate_decision`, `guardrails_decision`).
- `[src/orchestrator/state.py:AgentState]`: `TypedDict` specification for graph context propagation.
- `[src/orchestrator/state.py:RunSnapshot]`: Defaulted Pydantic model providing accessor views (`to_escalation_packet`, `to_audit_record`, `to_result`).
- `[src/orchestrator/wrappers.py:safe_node]`: Exception containment decorator applying node-specific fallback states upon runtime faults.
- `[src/orchestrator/nodes.py:normalize_node, classify_node, retrieval_node, routing_node, generation_node, guardrails_node, escalate_node, audit_node]`: Discrete task execution nodes.

## Invariants
- `[src/orchestrator/graph.py:build_graph]`: Every pipeline path converges on `audit_node` prior to `END`, guaranteeing an audit trail for 100% of inputs.
- `[src/orchestrator/wrappers.py:safe_node]`: Unhandled node exceptions are caught, recording degraded status (`is_degraded = True`), logging tracebacks in `error_details`, and gracefully routing to `escalate_node`.
- `[src/orchestrator/graph.py:route_decision]`: Tickets route to `generate` only when `routing_action == "AUTO_RESPOND"`; all other statuses divert to `escalate`.

## Side Effects
- Invokes vector search in ChromaDB, network calls to remote LLM endpoints via the generation cascade, and synchronous disk writes to SQLite in `audit_node`.

## Verification
- Run: `pytest tests/integration/test_orchestrator.py tests/integration/test_resilience.py tests/integration/test_audit_log.py -v`

