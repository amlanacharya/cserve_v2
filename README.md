# CloudServe Support Orchestrator Blueprint

## System Overview

The **CloudServe Support Orchestrator** is a decoupled, modular monolith processing pipeline designed for enterprise customer support operations. It ingests multi-channel customer inquiries, classifies intent and urgency, retrieves grounded knowledge base passages from 29 curated documentation articles using ChromaDB, routes tickets through independent dual gates (intent confidence and retrieval similarity), synthesizes citation-backed answers with strict source anchors (`[DOC-ID]`), and enforces active safety guardrails against PII leakage and hallucination.

The system is coordinated by a LangGraph `StateGraph`, wrapped with `@safe_node` fault-tolerant exception containment, backed by an append-only SQLite decision audit log, and powered by a resilient 3-tier provider cascade (OpenRouter $\rightarrow$ Google Gemini $\rightarrow$ offline fail-safe escalation engine).

---

## Measured results (validation set, 8 Nov 2026)

80 tickets, unattended run, report in `evaluation/validation_report.json`: **FCR 23.8% (target 65%, not met; 7.5% before tuning)**, intent accuracy 85.0%, ECE 0.093, retrieval precision@3 92.5%, P95 latency 8.2 s on a rate-limited free tier (budget 3 s, not met), 0 crashes, 80/80 decisions logged, 0 of 14 must-not-automate tickets auto-answered; 25 tickets fell back because the provider rate-limited. All four runs and how each change was chosen are in `02_Report/` section 7 and `evaluation/results/`.

**Development-set benchmark (500 tickets, three low-cost providers in rotation, about $0.03):** 500/500 processed with no provider fallbacks, FCR 32.2%, intent accuracy 86.4%, ECE 0.056, 2 of 87 must-not tickets answered (a safety gap the 80-ticket set did not show), guardrail stops 41.8%. In-sample for the tuned components; see `02_Report/` section 7.7 and `evaluation/results/RUN_MANIFEST.md`. With `openai/gpt-oss-120b` (OpenRouter only, ~$0.10): FCR 44.2% (221/500), 1 of 87 must-not answered, P95 7.4 s. Ceiling: only 62.2% of dev tickets (60% of validation) are labelled automatable, so 65% auto-resolved is not reachable without answering tickets labelled escalate. Validation run 5 on the same providers: FCR 20.0% (16/80), 0 fallbacks.

Providers are optional and configured in `.env` (see `.env.example`): `PROVIDER_ORDER`, `PROVIDER_STRATEGY=roundrobin`, `MAX_SPEND_USD`.

## Customer envelope, priority and feedback (added after the measured runs)

- `customer_message` on every auto-resolved result: the validated draft wrapped by `src/generation/formatter.py` with the machine disclaimer and a `Reference: [DOC-ID: Title]` footer. `final_response` (what the guardrails validated and the metrics count) is unchanged.
- `priority_score` / `priority_level` on every result (`src/routing/priority.py`): urgency base score plus a tier bonus. There is no live queue, so no `queue_position`.
- `POST /tickets/{ticket_id}/feedback`: stores a human agent's verdict in a separate `agent_feedback` table. `decision_log` stays append-only and untouched.
- These do not change routing, so the reported FCR/ECE/latency numbers still apply.

---

## Acceptance Criteria Traceability (A1–A12)

| Criterion | Requirement Description | Architectural Component / File |
|---|---|---|
| **A1** | Clean checkout launch | `requirements.txt`, `pyproject.toml`, and `.env.example`. |
| **A2** | 4-channel ingestion | `src/ingest/normalizer.py` parsing `email`, `chat`, `docs_comment`, and `forum`. |
| **A3** | Intent & urgency classification | `src/classify/classifier.py` emitting intent, intent alternatives, urgency, and confidence. |
| **A4** | Grounded retrieval | `src/retrieval/store.py` querying ChromaDB over header-chunked `05_Datasets/documentation.json`. |
| **A5** | Deterministic routing | `src/routing/router.py` evaluating independent orthogonal gates ($c \ge 0.75$, $s_{\text{ret}} \ge 0.65$). |
| **A6** | Verifiable answer citations | `src/generation/generator.py` enforcing strictly grounded `[DOC-ID]` citations. |
| **A7** | Active guardrail blocking | `src/guardrails/` (`pii.py`, `hallucination.py`) suppressing tripped drafts and diverting to escalation. |
| **A8** | Persistent decision log | `src/audit/logger.py` append-only SQLite `decision_log` table reconciling 100% of processed tickets. |
| **A9** | Unattended evaluation run | `evaluation/harness.py` batch CLI taking `--input`, `--output`, and `--delay`. |
| **A10** | Automated metrics report | `evaluation/metrics.py` computing volume, business (FCR), technical (latency, ECE), and governance metrics. |
| **A11** | Fault-tolerant execution | `@safe_node` wrappers on all nodes plus 3-tier cascade (OpenRouter $\rightarrow$ Gemini $\rightarrow$ offline mock). |
| **A12** | Single-command test suite | `pytest tests/ -v` covering unit modules, graph failure recovery, and end-to-end flows. |

---

## Subdirectories & System Boundaries

- **[src](./src/README.md)**: Core application subsystem and REST service. Houses the FastAPI web server (`src/api.py`), pipeline state graph, and nine specialized domain packages:
  - **[src/audit](./src/audit/README.md)**: Append-only SQLite WAL store enforcing database-level immutability triggers.
  - **[src/classify](./src/classify/README.md)**: 21-intent classification taxonomy, confidence estimation, and non-negotiable safety veto checks.
  - **[src/core](./src/core/README.md)**: Canonical Pydantic schemas, runtime literal types, threshold configurations, and PII regexes.
  - **[src/generation](./src/generation/README.md)**: Resilient 3-tier LLM cascade and XML-sandboxed prompt generation.
  - **[src/guardrails](./src/guardrails/README.md)**: Post-generation PII scrubbing and lexical unigram entailment verification.
  - **[src/ingest](./src/ingest/README.md)**: Multi-channel normalizer standardizing tickets into `CanonicalTicket` instances.
  - **[src/orchestrator](./src/orchestrator/README.md)**: LangGraph state machine with `@safe_node` fault-tolerant containment.
  - **[src/retrieval](./src/retrieval/README.md)**: Header-based Markdown document chunker and ChromaDB dense vector store.
  - **[src/routing](./src/routing/README.md)**: Deterministic orthogonal dual-gate routing logic and human triage escalation packets.
- **[evaluation](./evaluation/README.md)**: Unattended batch evaluation CLI (`evaluation/harness.py`) and quantitative metrics engine (`evaluation/metrics.py`) computing FCR rate, calibration error, and latency percentiles.

---

## Global Invariants

- **Orthogonal Dual-Gate Routing**: Automated resolution (`AUTO_RESOLVED`) requires all four conditions: intent confidence $c \ge 0.75$, retrieval similarity $s_{\text{ret}} \ge 0.65$, urgency $\ne \text{"CRITICAL"}$, and `must_not_auto_respond == False`.
- **Append-Only Audit Reconciliation**: 100% of processed tickets converge on `audit_node` and write to the SQLite `decision_log` table. SQLite database triggers unconditionally abort `UPDATE` and `DELETE` operations.
- **Inbound & Outbound Safety Containment**: PII is scrubbed during ingestion and audited via `pii_redactions_count`. Generated drafts tripping guardrails ($< 50\%$ lexical unigram overlap, hallucinated citations, or leaked credentials) are suppressed and escalated.
- **Degraded Execution Isolation**: Node exceptions caught by `@safe_node` mark `is_degraded = True`, append to `failed_nodes`, and route safely to `escalate_node` without terminating the host process.

---

## Global Side Effects

- **SQLite WAL Storage**: Synchronous write-ahead log operations to `data/decision_log.db`.
- **Vector Database**: Disk access and embedding index management at `data/chromadb` (`duckdb+parquet`).
- **External Network Inference**: Outbound HTTPS requests to OpenRouter (`openrouter.ai`) and Google Gemini (`generativelanguage.googleapis.com`) API endpoints.

---

## System Verification

Run the complete test suite across unit modules, integration flows, and resilience tests:
```bash
pytest tests/ -v
```

### Quickstart Verification Run
```bash
# Verify ingestion & PII normalization
pytest tests/unit/test_ingest.py -v

# Verify retrieval & ChromaDB chunking
pytest tests/unit/test_retrieval.py -v

# Verify classification, routing, and audit logging
pytest tests/unit/test_classify.py tests/unit/test_routing.py tests/unit/test_audit.py -v

# Verify generation & active guardrails
pytest tests/unit/test_generation.py tests/unit/test_guardrails.py -v

# Verify LangGraph orchestration & failure recovery
pytest tests/integration/test_orchestrator.py tests/integration/test_resilience.py tests/integration/test_audit_log.py -v
```
