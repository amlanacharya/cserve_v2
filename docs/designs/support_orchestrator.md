# CloudServe Support Orchestrator System Architecture

*   **Author:** Amlan Acharya
*   **Status:** Proposed (Final, incorporating review stages 5–8)
*   **Date:** 2026-10-31

--------------------------------------------------------------------------------

## Overview

The CloudServe Support Orchestrator is a decoupled, modular monolith processing pipeline. It ingests multi-channel customer inquiries, classifies intent and urgency, retrieves grounded knowledge base passages, routes tickets through two independent gates (intent confidence and retrieval similarity), synthesizes citation-backed answers, and enforces active safety guardrails. It pairs an automated first-contact resolution engine with an enriched, fail-safe human escalation packet builder, satisfying all 12 project acceptance criteria (A1–A12).

## Problem Statement

CloudServe's customer support operations face several scaling bottlenecks:

1. **Low First-Contact Resolution (FCR)**: Current FCR is 42%, far short of the 65% target.
2. **Repetitive Inquiries**: Approximately 70% of inbound tickets are repeat inquiries (password lockouts, rate limits, invoices, rollback loops) with known solutions.
3. **Documentation Retrieval Failure**: Support agents struggle to find answers across the 29 curated knowledge base articles because keyword search fails on vocabulary mismatch (e.g., a customer writes "deployment keeps dying" while the article is titled "resolving container health check failures"). Non-fluent English inquiries widen this gap.
4. **Escalation Inefficiency**: 50% of tickets escalated to Tier 2 could be resolved by Tier 1 if findability and intent confidence were solved. Escalated tickets lack structured context, forcing senior engineers to repeat basic discovery.
5. **Operational and Trust Risk**: Incorrect automated responses directly damage customer trust. Critical production-downtime inquiries cannot wait, and informational answers require rigorous source attribution (`[DOC-ID]`).

The proposed solution is a modular monolith (`SupportOrchestrator`): strictly bounded domain modules coordinated by a LangGraph `StateGraph`, wrapped with `@safe_node` exception handlers, backed by deterministic SQLite decision logging and a 3-tier provider cascade that provides fault-tolerant execution (A11).

## Goals & Non-Goals

### Goals

*   **G1: Acceptance Criteria Fulfillment**: Satisfy all 12 project acceptance criteria (A1–A12).
*   **G2: Multi-Channel Canonical Ingestion**: Normalize raw inputs from four channels (`email`, `chat`, `docs_comment`, `forum`) into a single `CanonicalTicket` schema without validation exceptions.
*   **G3: Grounded Semantic Retrieval Prior to Routing**: Query the 29 documentation articles (chunked into 70–90 header-based chunks) using ChromaDB 0.3.21 and `all-MiniLM-L6-v2` embeddings in one step, so the retrieval score is available to the router.
*   **G4: Independent Dual-Gate Routing**: Route to automated response only when intent confidence $c \ge 0.75$ **and** retrieval similarity $s_{\text{ret}} \ge 0.65$ **and** urgency $\neq$ CRITICAL **and** no safety flag is set. The two scores are independent, orthogonal gates and are never blended.
*   **G5: Active Guardrails & Zero-Tolerance Escalation**: Block PII leaks and ungrounded claims; immediately divert tripped responses to human escalation without retry loops.
*   **G6: Fault-Tolerant 3-Tier Fallback Cascade**: Complete every ticket in every evaluation batch via an inference cascade (Groq $\rightarrow$ Google Gemini $\rightarrow$ offline fail-safe escalation engine).
*   **G7: Enriched Escalation Packaging**: Give human agents intent, urgency, confidence, intent alternatives, routing reason, and the top-2 candidate documentation links from the retrieval cache.
*   **G8: Modular Monolith Maintainability**: Enforce explicit domain boundaries, strict public interfaces, and zero circular dependencies.
*   **G9: Persistent Auditability & Measurable Evaluation**: Record every decision in an append-only SQLite store (`decision_log.db`) and compute evaluation metrics (A10) from it into JSON/CSV reports. SQLite and `evaluation/metrics.py` are the sole persistence and evaluation mechanisms.

### Non-Goals

*   **NG1: Live Telephony / Voice Processing**: Audio transcription and real-time voice handling are out of scope.
*   **NG2: Direct Ticketing System Write-Back**: Two-way sync or write-back to external ticket tools (e.g., Zendesk, Jira Service Desk) is out of scope. Output is delivered via API response, batch JSON exports, and SQLite audit logs.
*   **NG3: Autonomous Account Mutation**: Automated refunds, account modifications, or billing write-offs without human approval are strictly prohibited.
*   **NG4: Multi-Agent Recursive Debate**: Agent-to-agent debates and unconstrained agent loops are excluded to preserve determinism and latency bounds.
*   **NG5: Microservices Infrastructure Overhead**: Separate service containers, gRPC boundaries, and message queues are excluded in favor of an in-process modular monolith.
*   **NG6: External Experiment Tracking & Observability Daemons**: No experiment-tracking servers or telemetry collector daemons. All telemetry is local and SQLite/file-backed.
*   **NG7: Custom Rate-Limiter Infrastructure**: No token-bucket or leaky-bucket classes. Rate limits are handled by a configurable batch delay and retry backoff (see Section 11).
*   **NG8: Second Command-Line Interface**: The only entry points are the FastAPI service (`src/api.py`) and the batch CLI (`evaluation/harness.py`).

--------------------------------------------------------------------------------

## Proposed Architecture

### 1. System Configuration Parameters

| Parameter | Symbol | Default Value | Description |
|---|---|---|---|
| Intent Confidence Threshold | $\tau$ | `0.75` | Minimum intent classification confidence $c$ for automated response. |
| Retrieval Similarity Floor | $\sigma$ | `0.65` | Minimum cosine similarity $s_{\text{ret}}$ of the top retrieved chunk for automated response. |
| Top-K Document Chunks | $k_{\text{passages}}$ | `3` | Chunks retrieved for grounded generation. |
| Top-K Escalation Links | $k_{\text{escalate}}$ | `2` | Candidate documentation links attached to escalation packets. |
| Provider Request Timeout | $t_{\text{req}}$ | `10.0s` | Maximum HTTP request duration before a provider attempt fails. |
| Provider Max Retries | $n_{\text{retry}}$ | `1` | Retries per provider tier (timeouts, 5xx, and HTTP 429) before advancing the cascade. |
| Backoff Base / Cap | $b_0$ / $b_{\max}$ | `1.0s` / `8.0s` | Exponential backoff with full jitter on HTTP 429: sleep $\sim U(0,\ \min(b_{\max},\ b_0 \cdot 2^{n}))$. A `Retry-After` header, when present, takes precedence (capped at $b_{\max}$). |
| Batch Inter-Ticket Delay | `--delay` | `1.5s` | Sleep between tickets in `evaluation/harness.py`; `0` disables it. |
| Generation Temperature | $T_{\text{gen}}$ | `0.0` | Sampling temperature for classification and generation. |
| Chunk Target Range | n/a | `70–90` chunks | Expected chunk count for the 29-article corpus (asserted in tests). |

### 2. Acceptance Criteria Traceability Matrix

| Criterion | Requirement Description | Architectural Component / Mechanism |
|---|---|---|
| **A1** | Clean checkout launch | `06_Configuration/requirements.txt`, `pyproject.toml`, and README setup script. |
| **A2** | 4-channel ingestion | `src/ingest/normalizer.py` parsing `email`, `chat`, `docs_comment`, and `forum`. |
| **A3** | Intent & urgency classification | `src/classify/classifier.py` emitting intent, intent alternatives, urgency, and confidence $\in [0.0, 1.0]$. |
| **A4** | Grounded retrieval | `src/retrieval/store.py` querying ChromaDB over header-chunked `05_Datasets/documentation.json`. |
| **A5** | Deterministic routing | `src/routing/router.py` evaluating independent gates ($c \ge 0.75$, $s_{\text{ret}} \ge 0.65$) and safety flags. |
| **A6** | Verifiable answer citations | `src/generation/generator.py` enforcing strictly grounded `[DOC-ID]` citations. |
| **A7** | Active guardrail blocking | `src/guardrails/` (`pii.py`, `hallucination.py`) suppressing tripped drafts and diverting to escalation. |
| **A8** | Persistent decision log | `src/audit/logger.py` append-only SQLite `decision_log` table reconciling 100% of processed tickets. |
| **A9** | Unattended evaluation run | `evaluation/harness.py` batch CLI taking `--input`, `--output`, and `--delay`. |
| **A10** | Automated metrics report | `evaluation/metrics.py` computing volume, business (FCR), technical (latency, ECE), and governance metrics to JSON/CSV. |
| **A11** | Fault-tolerant execution | `@safe_node` wrappers on all LangGraph nodes plus the 3-tier cascade (Groq $\rightarrow$ Gemini $\rightarrow$ offline fail-safe engine). |
| **A12** | Single-command test suite | `pytest tests/ -v` covering unit modules, graph failure recovery, and end-to-end flows. |

### 3. Critical User Journeys (CUJs)

#### CUJ 1: Automated First-Contact Resolution with Grounded Citations
*   **Given**: A customer submits an inquiry about a standard operational issue covered by documentation.
*   **When**: The ticket is ingested, classified with $c \ge 0.75$, and retrieval returns a top chunk with $s_{\text{ret}} \ge 0.65$.
*   **Then**: The router selects `AUTO_RESPOND`. The generation node synthesizes a response citing `[DOC-ID]`, passes the PII and hallucination guardrails, writes the decision row to SQLite with `final_disposition = AUTO_RESOLVED`, and returns the response.

#### CUJ 2: Fail-Safe Enriched Human Escalation for Critical / Low-Confidence Inquiries
*   **Given**: A customer reports production downtime, or submits an ambiguous query that fails a confidence or retrieval gate.
*   **When**: The router detects `urgency == "CRITICAL"`, $c < 0.75$, $s_{\text{ret}} < 0.65$, or `must_not_auto_respond == true`.
*   **Then**: The pipeline selects `ESCALATE`, bypasses generation and guardrails, builds an `EscalationPacket` with the routing reason and top-2 candidate documentation links from the retrieval cache, logs `final_disposition = ESCALATED_ROUTER`, and hands off to human support.

#### CUJ 3: Active Guardrail Tripping and Safe Diversion
*   **Given**: A draft response contains customer PII or a claim not supported by retrieved context.
*   **When**: The guardrail module scans the draft and flags a violation.
*   **Then**: The draft is suppressed, the ticket is escalated with the violation diagnosis in the packet, `final_disposition = ESCALATED_GUARDRAIL` is logged, and no unverified text reaches the customer.

### 4. Architectural Topology & Modular Monolith Pattern

The system is an in-process **Modular Monolith**:

*   **Single Process Execution**: All domain logic runs in-process (no network hops between modules, no deployment overhead, one `uv` virtual environment).
*   **Clear Module Interfaces**: Each domain module (`ingest`, `classify`, `retrieval`, `routing`, `generation`, `guardrails`, `audit`) exposes its public functions through its package `__init__.py`.
*   **Core Shared Contracts (`src/core/`)**: Data models (`CanonicalTicket`, `DocumentChunk`, `EscalationPacket`, `ProcessedTicketResult`) and configuration loaders live in `src/core/`, preventing circular dependencies.
*   **Unified LangGraph Orchestration (`src/orchestrator/`)**: A single `StateGraph` coordinates the stages. Every node is wrapped with `@safe_node`, which intercepts exceptions, records degraded state, and ensures the graph reaches `END` (A11).
*   **Two Entry Points, One Workflow**: `src/api.py` (FastAPI) and `evaluation/harness.py` (batch CLI) both call the same `SupportOrchestrator` workflow.

#### Graph Topology (Conditional Branching)

The main path is `Ingest -> Classify -> Retrieve -> Route`. The router then selects exactly one of two branches. Both converge on `Audit`:

*   `AUTO_RESPOND`: `Generate -> Guardrails -> Audit`
*   `ESCALATE`: `EscalationBuilder -> Audit`

A conditional edge from `Guardrails` re-enters the escalation branch when a guardrail trips. A generation failure with no usable provider takes the same edge. This keeps a single escalation implementation.

```mermaid
flowchart TD
    Raw[Raw Inbound Ticket] --> Ingest[Ingest: normalize]
    Ingest --> Classify[Classify: intent, urgency, confidence]
    Classify --> Retrieve[Retrieve: ChromaDB top-k chunks]
    Retrieve --> Route{Route: c >= 0.75 AND s_ret >= 0.65 AND urgency != CRITICAL AND NOT must_not_auto_respond}

    Route -- AUTO_RESPOND --> Generate[Generate: grounded answer with DOC-ID citations]
    Generate --> Guardrails{Guardrails: PII and entailment}
    Guardrails -- PASSED --> Audit[(Audit: SQLite decision_log.db)]

    Route -- ESCALATE --> Esc[EscalationBuilder]
    Esc --> Audit

    Guardrails -- TRIPPED --> Esc
    Generate -- no provider output --> Esc
```

### 5. Directory Scaffolding

```text
├── pyproject.toml                     # uv project definition & editable package install
├── .env.example                       # API key & environment variable template
├── 06_Configuration/
│   └── requirements.txt               # Pinned dependencies (resolved for Python 3.11)
├── src/
│   ├── __init__.py
│   ├── api.py                         # FastAPI REST application: /health & /tickets/process
│   ├── core/                          # Cross-cutting contracts and configuration
│   │   ├── __init__.py
│   │   ├── config.py                  # Settings, thresholds (tau, sigma) & env validation
│   │   └── models.py                  # CanonicalTicket, DocumentChunk, EscalationPacket, ProcessedTicketResult
│   ├── ingest/                        # Channel normalization (email, chat, docs_comment, forum)
│   │   ├── __init__.py
│   │   └── normalizer.py
│   ├── classify/                      # Intent & urgency classification with sha256 cache
│   │   ├── __init__.py
│   │   ├── classifier.py
│   │   └── cache.py
│   ├── retrieval/                     # Header-based chunking, ChromaDB store & dense retrieval
│   │   ├── __init__.py
│   │   ├── chunker.py
│   │   └── store.py
│   ├── routing/                       # Independent-gate router & escalation builder
│   │   ├── __init__.py
│   │   ├── router.py
│   │   └── escalation.py
│   ├── generation/                    # Citation-grounded synthesis & 3-tier cascade
│   │   ├── __init__.py
│   │   ├── generator.py
│   │   ├── prompts.py                 # Static templates with XML-delimited untrusted input
│   │   └── cascade.py                 # Provider client, 429 backoff, offline fail-safe engine
│   ├── guardrails/                    # Active PII detector & citation entailment checker
│   │   ├── __init__.py
│   │   ├── pii.py
│   │   └── hallucination.py
│   ├── audit/                         # Append-only SQLite persistence (decision_log.db)
│   │   ├── __init__.py
│   │   └── logger.py
│   └── orchestrator/                  # Workflow assembly & LangGraph execution
│       ├── __init__.py
│       ├── state.py                   # State channel contracts & schema definitions
│       ├── graph.py                   # StateGraph assembly & conditional routing edges
│       ├── nodes.py                   # Graph node handlers
│       └── wrappers.py                # @safe_node fault tolerance wrapper
├── evaluation/
│   ├── __init__.py
│   ├── harness.py                     # Unattended batch CLI (--input, --output, --delay)
│   └── metrics.py                     # Volume, business, technical, governance metrics (JSON/CSV)
├── tests/
│   ├── unit/                          # Isolated module unit tests
│   │   ├── test_ingest.py
│   │   ├── test_classify.py
│   │   ├── test_retrieval.py
│   │   ├── test_routing.py
│   │   ├── test_generation.py
│   │   └── test_guardrails.py
│   └── integration/                   # End-to-end integration & fault resilience tests
│       ├── test_orchestrator.py
│       ├── test_audit_log.py
│       └── test_resilience.py
└── README.md                          # Quickstart, setup instructions & test commands
```

### 6. Data Models & Persistence Schema

Field lists below are the design contract. Pydantic models in `src/core/models.py` implement them; the DDL is executed by `src/audit/logger.py` on first run.

#### 6.1 `CanonicalTicket`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `ticket_id` | `str` | No | Unique ticket identifier (source ID, or generated UUID4 if absent). |
| `channel` | `Literal["email", "chat", "docs_comment", "forum"]` | No | Normalized source channel. |
| `subject` | `str \| None` | Yes | Subject or title; null for channels without one (e.g., chat). |
| `body` | `str` | No | Normalized inquiry text (whitespace-collapsed, markup stripped). |
| `sender_ref` | `str \| None` | Yes | Opaque customer reference; never raw PII beyond what the source provides. |
| `created_at` | `datetime` | No | Source timestamp (UTC); ingest time if the source has none. |
| `metadata` | `dict[str, Any]` | No | Channel-specific extras (thread ID, forum category); defaults to `{}`. |

#### 6.2 `DocumentChunk`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `chunk_id` | `str` | No | Unique chunk ID: `<DOC-ID>#<heading-slug>`, e.g. `DOC-014#rotating-api-keys`. |
| `doc_id` | `str` | No | Parent article ID used in `[DOC-ID]` citations. |
| `title` | `str` | No | Parent article title. |
| `heading_path` | `str` | No | Heading trail, e.g. `Troubleshooting > Health checks`. |
| `text` | `str` | No | Chunk body, prefixed with title and heading path for embedding context. |
| `ordinal` | `int` | No | Position of the chunk within the parent article (0-based). |
| `similarity` | `float \| None` | Yes | Cosine similarity in $[0, 1]$; populated only on query results. |

#### 6.3 `EscalationPacket`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `ticket_id` | `str` | No | Escalated ticket ID. |
| `final_disposition` | `Literal["ESCALATED_ROUTER", "ESCALATED_GUARDRAIL", "ESCALATED_ERROR"]` | No | Why the ticket was escalated. |
| `routing_reason` | `str` | No | Human-readable explanation (which gate or safety flag failed). |
| `inferred_intent` | `str` | No | Top intent label. |
| `intent_confidence` | `float` | No | Confidence $c$ for the top intent. |
| `intent_alternatives` | `dict[str, float]` | No | Other candidate intents and scores; `{}` if none. |
| `urgency` | `Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]` | No | Classified urgency. |
| `candidate_docs` | `list[DocumentChunk]` | No | Top-2 chunks from the retrieval cache; `[]` if retrieval failed. |
| `guardrail_violations` | `list[str]` | No | Violation diagnoses; `[]` unless a guardrail tripped. |
| `provider_used` | `str` | No | `groq`, `gemini`, or `offline_mock`. |
| `created_at` | `datetime` | No | Packet creation time (UTC). |

#### 6.4 `ProcessedTicketResult`

| Field | Type | Nullable | Description |
|---|---|---|---|
| `ticket_id` | `str` | No | Processed ticket ID. |
| `channel` | `str` | No | Source channel. |
| `final_disposition` | `Literal["AUTO_RESOLVED", "ESCALATED_ROUTER", "ESCALATED_GUARDRAIL", "ESCALATED_ERROR"]` | No | Terminal outcome. |
| `final_response` | `str \| None` | Yes | Verified customer response; null if escalated. |
| `citations` | `list[str]` | No | Validated `[DOC-ID]` citations; `[]` if escalated. |
| `escalation_packet` | `EscalationPacket \| None` | Yes | Populated whenever the ticket is escalated. |
| `inferred_intent` | `str` | No | Top intent label. |
| `intent_confidence` | `float` | No | Confidence $c$. |
| `urgency` | `str` | No | Classified urgency. |
| `top_retrieval_score` | `float` | No | Best chunk similarity $s_{\text{ret}}$; `0.0` if retrieval failed. |
| `routing_reason` | `str` | No | Audit explanation for the routing decision. |
| `provider_used` | `str` | No | Provider tier that produced the result. |
| `is_degraded` | `bool` | No | True if any node triggered safe degradation. |
| `latency_ms` | `float` | No | End-to-end elapsed time. |

#### 6.5 SQLite `decision_log` Table

Append-only. A surrogate key allows the same `ticket_id` to be reprocessed across runs while preserving history. Triggers reject `UPDATE` and `DELETE`.

| Column | SQLite Type | Nullable | Key / Constraint | Description |
|---|---|---|---|---|
| `id` | `INTEGER` | No | **PRIMARY KEY** `AUTOINCREMENT` | Surrogate row ID. |
| `run_id` | `TEXT` | No | Indexed | UUID of the batch run or API process session. |
| `ticket_id` | `TEXT` | No | Indexed | Ticket identifier. |
| `channel` | `TEXT` | No | `CHECK` in the four channels | Source channel. |
| `logged_at` | `TEXT` | No | ISO-8601 UTC | Row write time. |
| `inferred_intent` | `TEXT` | No | n/a | Top intent label. |
| `intent_confidence` | `REAL` | No | `CHECK` between 0 and 1 | Confidence $c$. |
| `intent_alternatives` | `TEXT` | No | JSON object, default `'{}'` | Alternative intents and scores. |
| `urgency` | `TEXT` | No | `CHECK` in `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | Classified urgency. |
| `top_retrieval_score` | `REAL` | No | `CHECK` between 0 and 1 | Retrieval similarity $s_{\text{ret}}$. |
| `must_not_auto_respond` | `INTEGER` | No | `CHECK` in 0, 1 | Safety flag at routing time. |
| `routing_action` | `TEXT` | No | `CHECK` in `AUTO_RESPOND`, `ESCALATE` | Router decision. |
| `routing_reason` | `TEXT` | No | n/a | Audit explanation. |
| `guardrail_status` | `TEXT` | Yes | `CHECK` in `PASSED`, `TRIPPED` when not null | Null if guardrails never ran. |
| `final_disposition` | `TEXT` | No | `CHECK` in the four dispositions | Terminal outcome. |
| `citations` | `TEXT` | No | JSON array, default `'[]'` | Validated `[DOC-ID]` list. |
| `provider_used` | `TEXT` | No | `CHECK` in `groq`, `gemini`, `offline_mock` | Provider tier used. |
| `is_degraded` | `INTEGER` | No | `CHECK` in 0, 1 | Safe-degradation flag. |
| `error_details` | `TEXT` | Yes | n/a | Diagnostic if an exception was caught. |
| `guardrail_violations` | `TEXT` | No | JSON array, default `'[]'` | Violation diagnoses when a guardrail tripped. |
| `latency_ms` | `REAL` | No | n/a | End-to-end latency. |

**Migration note**: `guardrail_violations` was added after the first release of this table. `AuditLogger._init_db` adds it to a pre-existing database with `ALTER TABLE decision_log ADD COLUMN guardrail_violations TEXT NOT NULL DEFAULT '[]'` when `PRAGMA table_info` shows it missing; rows written earlier read back as `[]`. The append-only triggers block `UPDATE` and `DELETE` only, so the `ALTER` is unaffected.

```sql
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
    latency_ms            REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decision_log_ticket ON decision_log (ticket_id);
CREATE INDEX IF NOT EXISTS idx_decision_log_run    ON decision_log (run_id);

CREATE TRIGGER IF NOT EXISTS decision_log_no_update BEFORE UPDATE ON decision_log
BEGIN SELECT RAISE(ABORT, 'decision_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS decision_log_no_delete BEFORE DELETE ON decision_log
BEGIN SELECT RAISE(ABORT, 'decision_log is append-only'); END;
```

### 7. Pipeline State Contract

The orchestrator state channels are governed by the following contract:

| State Key | Type Contract | Producing Node | Invariant / Description |
|---|---|---|---|
| `run_id` | `str` | Input | Unique run identifier for batch execution or API session audit reconciliation. |
| `raw_ticket` | `dict[str, Any]` | Input | Initial incoming customer inquiry payload. |
| `canonical_ticket` | `CanonicalTicket` | `normalize_node` | Canonical schema; never null after normalization. |
| `inferred_intent` | `str` | `classify_node` | One of the 21 dataset intent labels (`api_key_issue`, `authentication_failure`, `account_access`, `sso_configuration`, `billing_query`, `quota_or_overage`, `deployment_failure`, `rollback_request`, `rate_limit`, `performance_degradation`, `database_issue`, `security_incident`, `compliance_request`, `configuration_help`, `integration_help`, `webhook_issue`, `data_residency`, `data_export`, `feature_request`, `onboarding`, `unclear_request`), or `unknown` on classification failure (decision recorded in issue #10). |
| `intent_alternatives` | `dict[str, float]` | `classify_node` | Runner-up intents with scores; `{}` if none. Informational only; never used in the routing gate. |
| `urgency` | `Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]` | `classify_node` | Classified urgency level. |
| `confidence` | `float` | `classify_node` | Intent confidence $c \in [0.0, 1.0]$. Independent of retrieval similarity. |
| `must_not_auto_respond` | `bool` | `classify_node` / cascade | Safety veto: set for account-mutation requests (refund, deletion), legal or security-incident language, and always when the offline fail-safe engine produced the classification. |
| `retrieved_docs` | `list[DocumentChunk]` | `retrieval_node` | Top-$k$ chunks with IDs and cosine similarity scores. |
| `top_retrieval_score` | `float` | `retrieval_node` | Cosine similarity $s_{\text{ret}}$ of the best chunk. Independent of $c$. |
| `routing_action` | `Literal["AUTO_RESPOND", "ESCALATE"]` | `routing_node` | Deterministic decision from the independent gates and safety flags. |
| `routing_reason` | `str` | `routing_node` | Audit explanation naming every failed gate. |
| `draft_response` | `str \| None` | `generation_node` | Synthesized answer with `[DOC-ID]` citations; null on escalation. |
| `guardrail_status` | `Literal["PASSED", "TRIPPED"] \| None` | `guardrails_node` | PII and hallucination check result; null if guardrails did not run. |
| `escalation_packet` | `EscalationPacket \| None` | `escalate_node` | Populated whenever the ticket is escalated. |
| `final_response` | `str \| None` | `guardrails_node` | Verified response delivered to the customer; null if escalated. |
| `final_disposition` | `Literal["AUTO_RESOLVED", "ESCALATED_ROUTER", "ESCALATED_GUARDRAIL", "ESCALATED_ERROR"]` | `audit_node` | Terminal outcome; see mapping below. |
| `citations` | `list[str]` | `generation_node` | Validated `[DOC-ID]` citations. |
| `provider_used` | `str` | `generation_node` / `classify_node` | LLM tier used (`groq`, `gemini`, or `offline_mock`). |
| `execution_latency_ms` | `float` | Pipeline wrapper | End-to-end elapsed time in milliseconds. |
| `is_degraded` | `bool` | `@safe_node` | True if any node caught an error and degraded safely. |
| `error_details` | `str \| None` | `@safe_node` | Traceback or diagnostic if an exception was caught. |

**`final_disposition` mapping:**

| Value | Condition |
|---|---|
| `AUTO_RESOLVED` | Router chose `AUTO_RESPOND` and guardrails returned `PASSED`. |
| `ESCALATED_ROUTER` | Router chose `ESCALATE` (gate failure, `CRITICAL` urgency, `must_not_auto_respond`, or offline fail-safe engine). |
| `ESCALATED_GUARDRAIL` | Router chose `AUTO_RESPOND` but guardrails returned `TRIPPED`. |
| `ESCALATED_ERROR` | A node raised and `@safe_node` diverted the ticket, or generation had no usable provider output. |

### 8. Fault-Tolerant Node Execution (`@safe_node`)

To provide fault-tolerant execution (A11), every node is wrapped with `@safe_node`:

```python
def safe_node(node_name: str, fallback_action: str):
    """
    Catches all unhandled exceptions within a node, records the failure
    in state and audit log, and sets safe default state values so the graph
    progresses to END without aborting the process.
    """
```

*   **Failure in Classification**: `inferred_intent = "unknown"`, `confidence = 0.0`, `intent_alternatives = {}`, `urgency = "HIGH"`, `must_not_auto_respond = True`; routes to escalation.
*   **Failure in Retrieval**: `retrieved_docs = []`, `top_retrieval_score = 0.0`; routes to escalation.
*   **Failure in Generation**: The provider cascade fails over tier by tier. The offline fail-safe engine never generates an answer, so if both network tiers fail the ticket is escalated with `ESCALATED_ERROR`.
*   **Failure in Guardrails**: Zero-tolerance diversion to escalation with safety diagnostics (`ESCALATED_GUARDRAIL`).
*   **Failure in Audit**: The write is retried once; if it still fails, the result is returned with `is_degraded = True` and the failure is written to stderr so the reconciliation gap is visible (A8).

### 9. Retrieval: Header-Based Chunking & Unified Retrieval

1. **Chunking**: `src/retrieval/chunker.py` splits each Markdown article at **H2 and H3 headers**. Each section becomes one chunk. Sections that exceed the embedding model's useful window (~256 tokens) are split further at paragraph boundaries. Very short sections (under ~40 tokens) are merged into the preceding sibling. The 29 articles are expected to yield **70–90 chunks**, which is asserted in `test_retrieval.py`.
2. **DOC-ID Anchors**: Every chunk carries its parent `doc_id` and a stable anchor `chunk_id = <DOC-ID>#<heading-slug>`. Each chunk's embedded text is prefixed with the article title and heading path. Citations in answers use the article-level `[DOC-ID]`. The hallucination guardrail validates each cited ID against the `doc_id` of the chunks in state.
3. **Indexing**: ChromaDB 0.3.21 indexes the chunks with `all-MiniLM-L6-v2` embeddings (cosine space), persisted under `data/chromadb/`. Cosine similarity is computed as $1 - d_{\text{cosine}}$.
4. **Unified Retrieval Step**: Retrieval occurs **before** routing, once per ticket, using the subject plus normalized body. The top chunk's similarity is stored as $s_{\text{ret}}$.
5. **Cache Reuse**: When escalating, `EscalationBuilder` takes the top-2 chunks already in state. When auto-responding, the generator uses the top-3 chunks already in state. No second lookup occurs.

### 10. Independent-Gate Routing

Intent confidence $c$ comes from the classifier. Retrieval similarity $s_{\text{ret}}$ comes from the vector store. They are **independent, orthogonal gates**: neither score is blended into or used to adjust the other, and each is logged separately. A ticket must clear both.

$$\text{Action} = \begin{cases} \text{AUTO\_RESPOND} & \text{if } c \ge 0.75 \ \land\ s_{\text{ret}} \ge 0.65 \ \land\ \text{urgency} \neq \text{CRITICAL} \ \land\ \neg\,\text{must\_not\_auto\_respond} \\ \text{ESCALATE} & \text{otherwise} \end{cases}$$

The router is a pure function of state with no model calls. `routing_reason` lists every failed condition (for example, `c=0.62<0.75; s_ret=0.41<0.65`), so each escalation is explainable and the A5 determinism property holds.

Rationale for keeping the gates separate: a confident classifier can still be wrong about whether the knowledge base covers the question, and a strong retrieval match does not prove the customer's intent was understood. Blending the two would let a high score on one mask a failure on the other.

### 11. Provider Cascade, Prompt Safety & Rate-Limit Handling

#### 11.1 Three Tiers

Acceptance Criterion A11 requires handling provider timeouts, rate limits, and outages. The cascade has three tiers:

1. **Primary: Groq** via its OpenAI-compatible endpoint (`https://api.groq.com/openai/v1`, using the `openai` client). Generation uses `llama-3.3-70b-versatile`. Classification uses `llama-3.1-8b-instant`, which is faster and has separate, higher rate limits. Both model names are configurable in `src/core/config.py`.
2. **Secondary: Google Gemini** (`gemini-2.5-flash`). Independent infrastructure backup.
3. **Tertiary: Offline Fail-Safe Escalation Engine.** A local, deterministic engine with no network dependency:
   *   **Intent**: keyword and token-overlap matching against the intent label vocabulary.
   *   **Retrieval**: a local ChromaDB lookup to attach top-2 candidate documents to the packet.
   *   **Routing**: sets `must_not_auto_respond = True`, so the router **always** returns `ESCALATE`. The audit row records `provider_used = offline_mock` and a routing reason such as `OFFLINE_FALLBACK: all network providers unavailable`.
   *   **No generation**: it never attempts speculative or templated answer generation and never produces `draft_response`.

#### 11.2 Rate-Limit Mitigation (No Token-Bucket Classes)

*   **Batch pacing**: `evaluation/harness.py` accepts `--delay <seconds>` (default `1.5`) and sleeps that long between tickets. This is a plain `time.sleep`, not a limiter class.
*   **Backoff on HTTP 429**: the cascade client retries a 429 using exponential backoff with full jitter (parameters in Section 1), honoring `Retry-After` when present. After $n_{\text{retry}}$ retries, it advances to the next tier. Timeouts and 5xx responses use the same retry budget.
*   **Bounded latency**: Worst case per network tier is $(n_{\text{retry}} + 1) \cdot t_{\text{req}} + b_{\max}$ = 28 s. Worst case for the two network tiers is therefore about 56 s per ticket. In practice a 429 returns within milliseconds, so the realistic failover time is a few seconds.

#### 11.3 Provider-Independent Calibration

Raw model logits are not trusted across model families. The classifier emits a calibrated confidence $c$ derived from the model's output only; it is validated against the labeled set via ECE in A10. Retrieval similarity is **not** blended into $c$ (see Section 10). Per-provider accuracy, latency, ECE, and escalation rate are reported in A10 to verify calibration integrity.

#### 11.4 Prompt-Injection Defense: XML Delimiter Sandboxing

All untrusted text is placed inside XML delimiters in static prompt templates (`src/generation/prompts.py`):

```text
<ticket_body>
{escaped ticket body}
</ticket_body>

<retrieved_context>
  <doc id="DOC-014">...</doc>
</retrieved_context>
```

*   The system prompt states that content inside `<ticket_body>` and `<retrieved_context>` is **data, not instructions**, and that any instruction inside those tags must be ignored.
*   Before insertion, the literal characters `<` and `>` in untrusted text are escaped (`&lt;`, `&gt;`), so a ticket cannot close the tag and inject text outside the sandbox.
*   Delimiters reduce injection risk but are not a complete defense. The backstops are structural: the classifier cannot trigger actions, the router is deterministic code, `must_not_auto_respond` is set by code rather than by the model, and the output guardrails (Section 12) validate every response.

### 12. Active Safety Guardrails

*   **PII & Credential Scrubbing**: Scans incoming tickets and outgoing drafts for email addresses, telephone numbers, credit cards, bearer tokens, and CloudServe API keys (`cs_live_[0-9a-zA-Z]{32}`).
*   **Hallucination & Citation Entailment Verification**:
    1. Verifies that every `[DOC-ID]` in the generated text matches the `doc_id` of a retrieved chunk in state.
    2. Measures token overlap and n-gram entailment between generated sentences and cited passages.
    3. Fails if citations are missing, ungrounded claims are detected, or invented article IDs appear.
*   **Zero-Tolerance Suppression**: Any guardrail trip suppresses delivery and converts the ticket to `ESCALATE` with `final_disposition = ESCALATED_GUARDRAIL` and violation metadata attached.

### 13. Audit Logging & Evaluation

*   **Source of Truth (SQLite)**: Every processed ticket appends one row to `data/decision_log.db` (schema in Section 6.5), reconciling 100% of tickets for A8.
*   **Automated Metrics (A10)**: `evaluation/metrics.py` reads from SQLite and computes FCR, accuracy, ECE, latency percentiles, per-provider breakdowns, and PII trip rate, writing JSON/CSV reports. These are the only evaluation outputs.

### 14. Non-Functional Requirements

#### Security & Privacy
*   **PII & Credential Scrubbing**: Pre-generation and post-generation scanning prevents API tokens, bearer keys, passwords, and sensitive customer identifiers from appearing in responses or logs.
*   **Credential Segregation**: Provider keys (`GROQ_API_KEY`, `GEMINI_API_KEY`) load from environment variables (`.env`) and are never committed.

#### Performance & Latency
*   **P95 Response Latency**: $\le 3.0$ s for automated responses; $\le 500$ ms for tickets escalated by the router (early bypass of generation).
*   **Storage & Footprint**: The ChromaDB index over the 29 articles stays under 50 MB.
*   **Offline Determinism**: The offline fail-safe engine completes keyword matching and local lookup in under 100 ms per ticket.

#### Reliability & Rollout
*   **Fault-Tolerant Execution (A11)**: Every provider exception triggers fallback down the cascade. The cascade ends at the offline fail-safe engine, which escalates rather than aborting the process.
*   **Entry-Point Parity**: `src/api.py` and `evaluation/harness.py` both call the same `SupportOrchestrator` workflow.
*   **SQLite Concurrency**: The audit logger opens SQLite in WAL mode with a busy timeout and serializes writes through a single connection, so concurrent API requests do not corrupt or drop rows.

--------------------------------------------------------------------------------

## Alternatives Considered

### 1. Dual-Runner Orchestration Engine (LangGraph + Python DAG)
*   **Rationale for rejection**: Two workflow engines violate YAGNI, double maintenance, and risk state-transition divergence.
*   **Decision**: LangGraph is the sole workflow engine. Fault resilience (A11) comes from `@safe_node` wrappers, and provider failover is isolated in the cascade.

### 2. Experiment Tracking and Distributed Observability Stack
*   **Rationale for rejection**: This is an in-process batch CLI and modular monolith. Experiment-tracking servers, collector daemons, and extra tracking flags add operational fragility and network failure modes during unattended grading, and they duplicate what SQLite and `metrics.py` already provide.
*   **Decision**: SQLite `decision_log.db` is the sole persistence layer for A8 and A10, and `evaluation/metrics.py` (JSON/CSV) is the sole evaluation mechanism.

### 3. Second CLI Entry Point (`src/cli.py`)
*   **Rationale for rejection**: It duplicated `evaluation/harness.py` (batch) and `src/api.py` (single ticket) with no capability of its own.
*   **Decision**: Keep exactly two entry points.

### 4. Blended Routing Confidence
*   **Rationale for rejection**: Mixing model probability with retrieval similarity into one score hides which signal failed, makes ECE uninterpretable, and lets a strong score on one axis mask a weak score on the other.
*   **Decision**: Intent confidence $c$ and retrieval similarity $s_{\text{ret}}$ are independent gates (Section 10).

### 5. Token-Bucket Rate Limiter
*   **Rationale for rejection**: A custom limiter class is over-engineered for a sequential evaluation batch against free-tier APIs.
*   **Decision**: A configurable `--delay` between batch tickets, plus exponential backoff with jitter on HTTP 429 in the cascade client.

### 6. Offline Mock That Generates Answers
*   **Rationale for rejection**: Speculative answers from a keyword heuristic would bypass the quality bar that justifies the LLM tiers and could reach customers ungrounded.
*   **Decision**: The tertiary tier is a fail-safe escalation engine that always routes to `ESCALATE`.

### 7. HuggingFace Serverless in the LLM Cascade
*   **Rationale for rejection**: Cold-boot delays (30–60 s) and sporadic free-tier rate limits threaten latency bounds.
*   **Decision**: The cascade is Groq, Gemini, and the offline fail-safe engine.

### 8. Fixed-Size or Whole-Article Chunking
*   **Rationale for rejection**: Whole articles dilute embeddings across unrelated sections. Fixed-size windows cut procedures mid-step and lose heading context.
*   **Decision**: Markdown H2/H3 header-based chunking with DOC-ID anchors (Section 9).

### 9. Speculative Vector DB Cache Warming
*   **Rationale for rejection**: Embedding about 80 chunks with `all-MiniLM-L6-v2` takes seconds on CPU.
*   **Decision**: ChromaDB initializes at startup (or lazily) with local persistence in `data/chromadb/`.

### 10. Runtime Dynamic Prompt Optimization (DSPy)
*   **Rationale for rejection**: Stage 3 requires a human-maintained prompt library with static version history ([Stage_3_Prompt_Library.docx](file:///c:/Users/amlan/Downloads/cloudserve/FDE_Capstone_Complete/Capstone_Pack/02_Stage_Workbooks/Stage_3_Prompt_Library.docx)). Compiling prompts at runtime burns tokens and risks rate limits.
*   **Decision**: Static prompt templates with `temperature=0.0` and `sha256` exact-match caching (A5).

--------------------------------------------------------------------------------

## Risks & Mitigations

Likelihood (L) and Impact (I) are rated Low, Medium, or High.

| ID | Risk | L | I | Mitigation | Residual Signal |
|---|---|---|---|---|---|
| R1 | Free-tier HTTP 429 rate limits stall or fail evaluation batches. | High | Medium | `--delay 1.5` between tickets; exponential backoff with full jitter and `Retry-After` on 429; cascade failover; classification on the higher-limit `llama-3.1-8b-instant`. | Per-provider 429 and failover counts in A10. |
| R2 | A configured provider model is deprecated or renamed. | Medium | Medium | Model names live in config, not code; `.env.example` documents them; the cascade falls through to Gemini and then the offline engine on a model-not-found error. | `provider_used` mix shifts toward `gemini` or `offline_mock`. |
| R3 | Prompt injection in ticket text or retrieved content. | Medium | High | XML delimiter sandboxing with tag escaping; routing and safety flags set by code; output PII and citation guardrails; no tools or write actions reachable from the model. | Guardrail trip rate; red-team cases in `test_guardrails.py`. |
| R4 | Ungrounded or hallucinated answers reach customers. | Medium | High | Guardrail verifies `[DOC-ID]` membership and n-gram entailment; any trip escalates; $s_{\text{ret}} \ge 0.65$ gate before generation. | `ESCALATED_GUARDRAIL` rate; hallucination trip count. |
| R5 | Thresholds ($\tau$, $\sigma$) are miscalibrated, causing over-escalation (low FCR) or unsafe auto-response. | Medium | High | Independent gates make each tunable and auditable; ECE and FCR measured on the validation set; thresholds are config values, not code constants. | ECE, FCR, and escalation rate in A10. |
| R6 | Header-based chunking yields poor chunks (articles with few headers, or a chunk count outside 70–90). | Medium | Medium | Size-based split and short-section merge rules; chunk-count assertion in tests; retrieval hit-rate test on known query-to-article pairs. | `test_retrieval.py` failures; low $s_{\text{ret}}$ distribution. |
| R7 | The offline fail-safe engine over-escalates when providers are down, depressing FCR. | Medium | Low | This is deliberate: a missed auto-resolution costs less than a wrong answer. The packet still carries candidate docs. The A10 report separates offline-tier results. | Share of `offline_mock` rows per run. |
| R8 | Dependency incompatibility (`chromadb==0.3.21`, `sentence-transformers`, `openai`, `langchain-openai`) breaks a clean checkout. | Medium | High | Pinned requirements resolved for Python 3.11; `openai>=1.10.0,<2.0.0`; A1 verified from a fresh venv. | A1 build check fails. |
| R9 | PII false negatives in scanning. | Low | High | Layered regexes (email, phone, card with Luhn check, tokens, `cs_live_` keys); scan both inbound and outbound text; PII test corpus. | PII trip-rate trend; missed-PII test cases. |
| R10 | SQLite write contention or audit gaps under concurrent API use. | Low | Medium | WAL mode, busy timeout, single-writer connection; append-only triggers; reconciliation check in `test_audit_log.py`. | Row count differs from processed count. |
| R11 | Provider rate-limit failover makes the worst-case latency exceed SLA. | Low | Medium | Worst case bounded (about 56 s); the P95 3 s SLA applies to the normal path; router-escalated tickets bypass generation entirely. | P95 and max latency in A10. |

--------------------------------------------------------------------------------

## Detailed Implementation Plan

The implementation is partitioned into six sequential, incremental phases aligned with the five-day build checkpoints in the Build Specification. Each phase leaves the codebase in a stable, buildable, and testable state verified by explicit test commands.

### Phase 1: Environment, Core Models, Ingestion & Inbound Sanitization (Day 1 Milestone)

*   **Objective**: Configure the Python 3.11 build environment, establish core Pydantic contracts, and implement multi-channel ingestion with inbound PII scrubbing.
*   **Target Files**:
    *   `[Modify] 06_Configuration/requirements.txt`: Update pinned dependencies to include `openai>=1.10.0,<2.0.0`, `langgraph>=0.0.26`, `chromadb==0.3.21`, `sentence-transformers>=2.2.2`, `sqlalchemy==2.0.0`, `fastapi>=0.109.0`, `uvicorn>=0.27.0`, `pydantic>=2.5.0`, `httpx>=0.26.0`, `python-dotenv>=1.0.0`, `pytest>=7.4.0`, and `pytest-asyncio>=0.23.0`.
    *   `[Create] pyproject.toml`: Configure editable package install for `src` using `setuptools` or `hatchling` under `uv`.
    *   `[Create] .env.example`: Template declaring `GROQ_API_KEY`, `GEMINI_API_KEY`, `GROQ_GEN_MODEL=llama-3.3-70b-versatile`, `GROQ_CLASSIFY_MODEL=llama-3.1-8b-instant`, `GEMINI_MODEL=gemini-2.5-flash`, and default thresholds.
    *   `[Create] src/__init__.py`: Package root marker.
    *   `[Create] src/core/__init__.py`: Export core models and settings.
    *   `[Create] src/core/config.py`: Implement centralized `Settings` loading environment variables with defaults for $\tau = 0.75$, $\sigma = 0.65$, timeouts, and retry parameters.
    *   `[Create] src/core/models.py`: Implement Pydantic models for `CanonicalTicket`, `DocumentChunk`, `EscalationPacket`, and `ProcessedTicketResult` strictly matching Section 6 schemas.
    *   `[Create] src/ingest/__init__.py`: Export `normalize_ticket(raw_payload: dict) -> CanonicalTicket`.
    *   `[Create] src/ingest/normalizer.py`: Implement multi-channel parsing:
        *   `email`: Extract `subject`, `body`, and map `from` to `sender_ref`.
        *   `chat`: Map `message` to `body`, `user_id` to `sender_ref`, and set `subject = None`.
        *   `docs_comment`: Map `comment_text` to `body`, preserve `doc_id` in `metadata`, and set `subject = None`.
        *   `forum`: Map `post_title` to `subject` and `post_content` to `body`.
        *   Inbound Sanitization: Redact raw credit card numbers, email addresses, phone numbers, and API keys (`cs_live_[0-9a-zA-Z]{32}`) from `body` before constructing `CanonicalTicket`.
        *   Text Normalization: Collapse multiple whitespace characters and strip HTML tags without modifying technical identifiers.
    *   `[Create] tests/unit/test_ingest.py`: Verify canonical normalization, field aliasing, and inbound PII redaction across all four channels.
*   **Checkpoint Gate (Day 1)**:
    ```bash
    pytest tests/unit/test_ingest.py -v
    ```
    Asserts that 100% of sample payloads from all four channels parse into valid `CanonicalTicket` instances without schema errors (A2).

---

### Phase 2: Knowledge Base Chunking, Vector Storage & Traceable Retrieval (Day 2 Milestone)

*   **Objective**: Split the 29 documentation articles into semantic chunks, generate embeddings, and establish traceable ChromaDB retrieval.
*   **Target Files**:
    *   `[Create] src/retrieval/__init__.py`: Export `chunk_article`, `index_documentation`, and `query_documents`.
    *   `[Create] src/retrieval/chunker.py`: Implement Markdown header-based chunking:
        *   Parse articles from `05_Datasets/documentation.json`.
        *   Split at H2 (`##`) and H3 (`###`) headers.
        *   Prefix each chunk's embedding text with its article title and heading trail (`Title > Heading > Text`).
        *   Split sections exceeding 256 words at paragraph boundaries with 30-word overlap.
        *   Merge trailing sections under 40 words into their preceding sibling chunk.
        *   Assign deterministic `chunk_id = f"{doc_id}#{slugify(heading_text)}"`.
        *   Assert total chunk count across 29 articles falls within 70–90 chunks.
    *   `[Create] src/retrieval/store.py`: Implement ChromaDB 0.3.21 store:
        *   Persist collection `cloudserve_kb` under `data/chromadb/`.
        *   Use `sentence-transformers/all-MiniLM-L6-v2` for dense embeddings.
        *   Implement idempotent `index_documentation()`: check collection count; if matching expected chunk count, skip re-indexing to ensure sub-second startup.
        *   Implement `query_documents(query_text: str, top_k: int = 3) -> list[DocumentChunk]`: query ChromaDB, convert cosine distance $d$ to similarity $s_{\text{ret}} = 1 - d$, and return sorted chunks.
    *   `[Create] tests/unit/test_retrieval.py`: Test chunking output bounds (70–90 chunks), metadata preservation (`doc_id`), and similarity scoring against sample queries.
*   **Checkpoint Gate (Day 2)**:
    ```bash
    pytest tests/unit/test_retrieval.py -v
    ```
    Asserts that all 29 articles are indexed, chunk counts fall in 70–90, and top retrieved passages match expected ground truth articles with $s_{\text{ret}} \ge 0.65$ (A4).

---

### Phase 3: Classification, Deterministic Routing & SQLite Audit Persistence (Day 3 Milestone)

*   **Objective**: Implement intent and urgency classification, deterministic dual-gate routing, and append-only SQLite decision logging.
*   **Target Files**:
    *   `[Create] src/classify/__init__.py`: Export `classify_ticket`.
    *   `[Create] src/classify/cache.py`: In-memory and file-backed deterministic cache keyed on `sha256(canonical_ticket_json)` (A5).
    *   `[Create] src/classify/classifier.py`: Query Groq `llama-3.1-8b-instant` (temperature 0.0) with static prompt requesting JSON output:
        ```json
        {
          "inferred_intent": "<one of the 21 dataset intent labels>",
          "intent_alternatives": {"<intent>": <score>},
          "urgency": "LOW | MEDIUM | HIGH | CRITICAL",
          "confidence": <float between 0.0 and 1.0>
        }
        ```
        Evaluate safety veto: set `must_not_auto_respond = True` if inquiry matches regex `(refund|billing\s+adjustment|delete\s+my\s+account|legal\s+action|attorney|subpoena|security\s+vulnerability|breach|exploit|talk\s+to\s+a\s+human|agent)`.
    *   `[Create] src/routing/__init__.py`: Export `evaluate_route` and `build_escalation_packet`.
    *   `[Create] src/routing/router.py`: Pure-function routing gate evaluating independent criteria:
        $$\text{Action} = \begin{cases} \text{AUTO\_RESPOND} & \text{if } c \ge 0.75 \land s_{\text{ret}} \ge 0.65 \land \text{urgency} \neq \text{CRITICAL} \land \neg \text{must\_not\_auto\_respond} \\ \text{ESCALATE} & \text{otherwise} \end{cases}$$
        Generate detailed `routing_reason` articulating every passing and failing condition.
    *   `[Create] src/routing/escalation.py`: Implement `EscalationBuilder` assembling `EscalationPacket` using top-2 retrieved candidate chunks from state.
    *   `[Create] src/audit/__init__.py`: Export `log_decision` and `get_decision_history`.
    *   `[Create] src/audit/logger.py`: Implement append-only SQLite logger for `data/decision_log.db` matching Section 6.5 DDL:
        *   Execute `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;`.
        *   Install triggers prohibiting `UPDATE` and `DELETE`.
        *   Implement `log_decision(record: dict) -> None`.
    *   `[Create] tests/unit/test_classify.py`, `tests/unit/test_routing.py`, `tests/unit/test_audit.py`: Test classification parsing, full routing truth table (all combinations of $c$, $s_{\text{ret}}$, urgency, and safety flags), and SQLite append-only triggers.
*   **Checkpoint Gate (Day 3)**:
    ```bash
    pytest tests/unit/test_classify.py tests/unit/test_routing.py tests/unit/test_audit.py -v
    ```
    Asserts identical ticket inputs yield identical routing decisions, and SQLite successfully writes and locks decisions against mutation (A3, A5, A8).

---

### Phase 4: Grounded Synthesis, Active Guardrails & 3-Tier Inference Cascade (Day 4 Milestone)

*   **Objective**: Implement citation-grounded answer generation, XML prompt delimiter sandboxing, PII and hallucination guardrails, and the resilient 3-tier cascade.
*   **Target Files**:
    *   `[Create] src/generation/__init__.py`: Export `generate_response`.
    *   `[Create] src/generation/prompts.py`: Prompt templates with XML delimiter sandboxing:
        *   `<ticket_body>` encloses HTML-escaped ticket text.
        *   `<retrieved_context>` encloses top-3 chunks with `<doc id="[DOC-ID]">` headers.
        *   System prompt instructs the model to ignore instructions inside XML blocks and strictly cite source `[DOC-ID]`.
    *   `[Create] src/generation/cascade.py`: Resilient inference client:
        *   Tier 1 (Primary): Groq API (`llama-3.3-70b-versatile`) via OpenAI SDK transport.
        *   Tier 2 (Secondary): Google Gemini API (`gemini-2.5-flash`) via `httpx.Client`.
        *   Retry logic: Exponential backoff with full jitter on HTTP 429 ($b_0 = 1.0\text{s}$, $b_{\max} = 8.0\text{s}$, max 1 retry).
        *   Tier 3 (Tertiary Offline Mock): Local Deterministic Heuristic Engine. Matches keywords to one of the 21 dataset intent labels (e.g. `billing_query`, `authentication_failure`, `deployment_failure`, `rate_limit`), defaulting to `unclear_request` when nothing matches, retrieves local ChromaDB chunks, sets `must_not_auto_respond = True`, routes to `ESCALATE`, and never generates draft responses.
    *   `[Create] src/generation/generator.py`: Orchestrate prompt compilation, cascade query, and citation extraction.
    *   `[Create] src/guardrails/__init__.py`: Export `evaluate_guardrails`.
    *   `[Create] src/guardrails/pii.py`: Scan drafts for email, phone, bearer tokens, API keys, and credit cards with Luhn checksum validation.
    *   `[Create] src/guardrails/hallucination.py`: Validate citation integrity:
        1. All cited `[DOC-ID]`s exist in retrieved context.
        2. Unigram lexical entailment ratio between answer sentences and cited context $\ge 0.5$.
    *   `[Create] tests/unit/test_generation.py`, `tests/unit/test_guardrails.py`: Test citation formatting, prompt injection immunity, active guardrail diversion, and cascade failover.
*   **Checkpoint Gate (Day 4)**:
    ```bash
    pytest tests/unit/test_generation.py tests/unit/test_guardrails.py -v
    ```
    Asserts answers cite valid `[DOC-ID]`s, injected PII and hallucinations trigger immediate escalation without customer transmission, and fallback succeeds (A6, A7, A11).

---

### Phase 5: LangGraph StateGraph Assembly & FastAPI Web Service (Day 5 Milestone — Part 1)

*   **Objective**: Assemble domain modules into a compiled LangGraph workflow, wrap nodes with `@safe_node` exception containment, and expose the REST service.
*   **Target Files**:
    *   `[Create] src/orchestrator/__init__.py`: Export `SupportOrchestrator`.
    *   `[Create] src/orchestrator/state.py`: Implement `AgentState` TypedDict matching Section 7 State Contract table, including `run_id`, `must_not_auto_respond`, `intent_alternatives`, and `final_disposition`.
    *   `[Create] src/orchestrator/wrappers.py`: Implement `@safe_node` decorator catching all unhandled exceptions, recording `is_degraded = True` and `error_details`, and applying safe default fallbacks.
    *   `[Create] src/orchestrator/nodes.py`: Graph node handlers wrapping module operations (`normalize_node`, `classify_node`, `retrieval_node`, `routing_node`, `generation_node`, `guardrails_node`, `escalate_node`, `audit_node`).
    *   `[Create] src/orchestrator/graph.py`: Compile LangGraph `StateGraph`:
        *   `normalize_node` $\rightarrow$ `classify_node` $\rightarrow$ `retrieval_node` $\rightarrow$ `routing_node`.
        *   Conditional routing edge: `AUTO_RESPOND` $\rightarrow$ `generation_node`; `ESCALATE` $\rightarrow$ `escalate_node`.
        *   `generation_node` conditional edge: if draft generated $\rightarrow$ `guardrails_node`; if provider failed $\rightarrow$ `escalate_node`.
        *   `guardrails_node` conditional edge: `PASSED` $\rightarrow$ `audit_node`; `TRIPPED` $\rightarrow$ `escalate_node`.
        *   `escalate_node` $\rightarrow$ `audit_node` $\rightarrow$ `END`.
    *   `[Create] src/api.py`: FastAPI REST application exposing:
        *   `GET /health`: Returns `{"status": "ok"}`.
        *   `POST /tickets/process`: Consumes raw JSON ticket payload, passes through `SupportOrchestrator`, and returns `ProcessedTicketResult`.
    *   `[Create] tests/integration/test_orchestrator.py`: End-to-end integration test verifying both auto-response and escalation paths through the graph.
*   **Checkpoint Gate (Day 5.1)**:
    ```bash
    pytest tests/integration/test_orchestrator.py -v
    ```
    Asserts both automated and escalated execution paths traverse the LangGraph StateGraph cleanly to `END` and write valid audit records (A8, A11).

---

### Phase 6: Batch Evaluation CLI, Automated Metrics Report & Complete Test Suite (Day 5 Milestone — Part 2)

*   **Objective**: Implement unattended batch evaluation CLI, compute multi-dimensional metrics (volume, business, technical, governance), configure test fixtures, and author README documentation.
*   **Target Files**:
    *   `[Create] evaluation/__init__.py`: Package root marker.
    *   `[Create] evaluation/harness.py`: Batch CLI supporting `--input <file>`, `--output <file_or_dir>`, and `--delay <float>` (default `1.5s`). Loops sequentially over input tickets, executes `SupportOrchestrator`, and writes output reports.
    *   `[Create] evaluation/metrics.py`: Reads `decision_log.db` for the run and computes:
        *   Volume: Total tickets, auto-resolved count, escalated count, escalation breakdown (`ROUTER`, `GUARDRAIL`, `ERROR`).
        *   Business: Estimated First-Contact Resolution (FCR) rate.
        *   Technical: Accuracy against ground truth labels, retrieval precision@k, P50/P90/P95 latency percentiles, Expected Calibration Error (ECE with $M=10$ bins).
        *   Governance: PII detection rate, hallucination suppression rate, provider tier distribution (`groq`, `gemini`, `offline_mock`).
        *   Output formats: Detailed summary JSON (`validation_report.json`) and tabular CSV (`metrics_summary.csv`).
    *   `[Create] tests/conftest.py`: Shared test infrastructure:
        *   Mock HTTP transport fixtures for Groq and Gemini endpoints using custom `httpx.MockTransport` or monkeypatching.
        *   Isolated temporary directory ChromaDB fixture.
        *   Synthetic test ticket fixtures covering all edge cases.
    *   `[Create] tests/integration/test_resilience.py`: Fault injection tests validating `@safe_node` error containment, simulated HTTP 429 backoff, network disconnection fallback to offline mock, and SQLite WAL write concurrency.
    *   `[Create] tests/integration/test_audit_log.py`: Audit log reconciliation test confirming row count equals input ticket count and verifying append-only trigger enforcement.
    *   `[Create] README.md`: Setup instructions, single-command launch, test execution (`pytest tests/ -v`), and evaluation commands.
*   **Checkpoint Gate (Day 5.2 — Final Acceptance)**:
    ```bash
    pytest tests/ -v
    python -m evaluation.harness --input 05_Datasets/validation_tickets.json --output evaluation/validation_report.json --delay 1.5
    ```
    Asserts 100% of unit and integration tests pass, and unattended evaluation runs to completion producing valid metrics reports satisfying all 12 Acceptance Criteria (A1–A12).

--------------------------------------------------------------------------------

## Verification Plan

### 1. Environment & Build Verification (A1)
```bash
uv venv --python 3.11
# Windows activation:
.venv\Scripts\activate
# POSIX activation:
source .venv/bin/activate
uv pip install -e .
```

### 2. Full Test Suite Execution (A12)
```bash
pytest tests/ -v
```
All unit tests (`tests/unit/`) and integration tests (`tests/integration/`) must execute cleanly without warnings or failures.

### 3. Unattended Batch Evaluation Run (A9 & A10)
```bash
python -m evaluation.harness --input 05_Datasets/validation_tickets.json --output evaluation/validation_report.json --delay 1.5
```
Verifies batch completion across all 80 validation tickets, confirming:
1. `validation_report.json` and `metrics_summary.csv` are generated.
2. Volume metrics reconcile: `total_processed == len(validation_tickets)`.
3. Business metrics achieve FCR target $\ge 65\%$.
4. Calibration metrics report ECE $\le 0.15$.
5. Per-provider breakdowns confirm distribution across tiers.

### 4. Fault-Tolerance & Resilience Verification (A11)
```bash
pytest tests/integration/test_resilience.py -v
```
Simulates network outages and HTTP 429 responses to assert:
1. Every ticket completes without process termination.
2. HTTP 429 responses trigger exponential backoff with full jitter before failover.
3. Total provider failure falls back safely to the offline heuristic mock with `final_disposition = ESCALATED_ERROR`.
4. Tripped guardrails suppress response delivery and divert to `ESCALATED_GUARDRAIL`.

### 5. Audit Reconciliation & Immutability Verification (A8)
```bash
pytest tests/integration/test_audit_log.py -v
```
Asserts:
1. `SELECT COUNT(*) FROM decision_log WHERE run_id = ?` matches input ticket count exactly.
2. Direct `UPDATE` and `DELETE` queries on `decision_log` fail with `decision_log is append-only`.
