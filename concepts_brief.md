# CloudServe Support Orchestrator System Architecture

* **Author:** Amlan Acharya
* **Date:** 2026-10-30

## Overview

The CloudServe Support Orchestrator is a decoupled, deterministic sequential processing pipeline engineered to ingest multi-channel customer inquiries, classify intent and urgency, route tickets using calibrated confidence thresholds, retrieve grounded knowledge base passages, synthesize citation-backed answers, and enforce active safety guardrails. The system delivers an automated first-contact resolution engine paired with an enriched, fail-safe human escalation packet builder, satisfying all 12 project acceptance criteria (A1–A12).

## Discovery Evidence & Stakeholder Alignment

The system architecture is grounded in discovery findings from five primary stakeholder interviews and exploratory analysis of the 500-ticket development dataset:

1. **Marcus Adeyemi (Head of Customer Support)**: First Contact Resolution (FCR) is currently 42% (target: 65%). Marcus establishes the core reliability invariant: *"I would rather it said nothing than said something wrong."* Erroneous automated answers destroy customer trust. Precision must be prioritized over raw deflection volume.
2. **Sofia Restrepo (Tier 1 Support Agent)**: 70% of tickets are repeat inquiries with known answers (password lockouts, rate limits, invoice inquiries, rollback loops), but agents waste time searching for documentation because keyword search fails. Sofia requests an automated system that provides relevant documentation links and drafts without exposing agents to customer backlash from bad automated answers.
3. **Daniel Okonkwo (Tier 2 Support Engineer)**: 50% of escalations arriving at Tier 2 could be resolved by Tier 1 if findability and confidence were solved. Daniel specifies the exact requirements for an escalation hand-off packet: inferred intent, urgency, the relevant documentation links, and specific reasons for confidence failure ("show its working").
4. **Ines Varga (Technical Writer)**: The knowledge base comprises 29 curated articles. Keyword search fails due to vocabulary mismatch (e.g., customer queries "deployment keeps dying" vs. article title "resolving container health check failures"). Dense semantic vector retrieval is mandatory. Ines demands explicit citation tracking (`[DOC-ID]`) to audit whether errors stem from documentation gaps or model misinterpretation.
5. **Ravi Menon (Platform Lead & Customer)**: Emphasizes that downtime inquiries cannot tolerate waiting, while informational questions can. Ravi demands honest attribution: answers must cite their source and indicate automated origin so engineers can verify before taking production actions.

## Architecture Decisions & Pipeline Design

### 1. Orchestration Topology & Decoupled Execution
* **Pipeline Model**: A deterministic sequential pipeline with an early-routing compute branch and structured escalation packaging.
* **Core Engine Isolation**: The orchestration core resides in `src/orchestrator/engine.py` (`SupportOrchestrator`). Both the FastAPI REST service (`src/api.py`) and the batch CLI evaluation harness (`evaluation/harness.py`) consume this identical engine.
* **Execution Lifecycle**:
  1. `Ingest & Normalize`: Transform raw channel payloads into `CanonicalTicket`.
  2. `Classify`: Extract intent, urgency, and calibrated confidence score $\in [0.0, 1.0]$.
  3. `Routing Gate`: Evaluate routing conditions:
     - If `confidence < 0.75`, `urgency == "CRITICAL"`, or `must_not_auto_respond == true`: Route to **Escalation Path**.
     - Otherwise: Route to **Automated Response Path**.
  4. `Enriched Escalation Path` (Stakeholder-Grounded):
     - Execute lightweight ChromaDB retrieval to fetch top-2 candidate documentation links.
     - Build structured `EscalationPacket` (Intent, Urgency, Confidence, Routing Trigger Reason, Candidate Documentation Links).
     - Bypass LLM answer generation and guardrail evaluation (conserving compute and eliminating hallucination risk).
     - Log decision and return hand-off packet.
  5. `Automated Response Path`:
     - Query ChromaDB index over `05_Datasets/documentation.json` for top-3 relevant passages.
     - Generate grounded response with strict zero-temperature LLM inference.
     - Validate output via PII scrubber and citation entailment guardrail.
     - If guardrail trips: convert immediately to Escalation Path with guardrail failure diagnostics.
     - If passes: format verified response with `[DOC-ID]` citations and deliver.
  6. `Audit Log`: Record complete decision trace to append-only SQLite database (`decision_log.db`).

### 2. Ingestion & Canonical Schema Invariants
* **Canonical Schema (`CanonicalTicket`)**:
  - `ticket_id`: Unique identifier (string).
  - `channel`: Enum (`email`, `chat`, `docs_comment`, `forum`). Ingestion normalizer accepts and aliases `docs_comment` seamlessly.
  - `customer_id`: Extracted customer or organization ID.
  - `subject`: Ticket subject. Nullable or empty string supported without schema validation exceptions.
  - `body_text`: Core inquiry text.
  - `thread_history`: List of prior conversational messages for multi-turn chat and forum threads.
  - `metadata`: Channel-specific properties (e.g., documentation URL, thread depth).
* **Language Handling**: Inquiries with `language_fluency: "non_fluent"` are mapped into dense semantic vector space, bypassing vocabulary mismatches in keyword search.

### 3. Classification, Routing & Determinism (A3 & A5)
* **Deterministic Invariants**:
  - LLM classification runs with `temperature = 0.0` and fixed random seed.
  - Prompts enforce structured JSON schema output.
  - Exact match caching keyed on `sha256(canonical_ticket_json)` guarantees bitwise-identical decisions across runs.
* **Decision Thresholds**:
  - Routing threshold $\tau = 0.75$ calibrated against development dataset.
  - Safety override: `must_not_auto_respond == true` (e.g., ticket `DEV-0003` involving credential leaks or legal compliance) forces immediate escalation regardless of confidence.

### 4. Grounded Retrieval & Citation Verification (A4 & A6)
* **Storage & Indexing**: ChromaDB 0.3.21 initialized with `chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="..."))`.
* **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` indexing all 29 articles from `05_Datasets/documentation.json`. Indexing is pre-computed and persisted to prevent runtime latency during evaluation.
* **Citation Typography**: Strict format `[DOC-ID]` (e.g. `[DOC-AUTH-004]`). Responses without verifiable doc citations are blocked by the guardrail.

### 5. Active Guardrails & Zero-Crash Resilience (A7 & A11)
* **Guardrail Enforcement**:
  - **PII Guardrail**: Scans for API tokens, secret keys, passwords, and PII.
  - **Hallucination Blocker**: Verifies token overlap and semantic entailment against retrieved context.
  - **Zero-Tolerance Diversion**: On any safety trip, the system aborts automated delivery and escalates to human support with diagnostic logging. No recursive regeneration loops.
* **4-Tier Inference Cascade (A11)**:
  1. *Primary Provider*: Groq API (`llama-3.3-70b-versatile` / `openai/gpt-oss-120b`).
  2. *Secondary Provider*: Google Gemini API (`gemini-2.5-flash`).
  3. *Tertiary Provider*: HuggingFace Inference API.
  4. *Quaternary / Offline Fallback*: Deterministic local heuristic engine indexing `documentation.json`, ensuring 100% completion with zero runtime crashes even during total network blackout.

### 6. Codebase Structure
```text
src/
├── api.py                    # FastAPI service exposing /health and /tickets/process
├── orchestrator/engine.py    # Pipeline coordinator & state transitions
├── ingestion/normalizer.py   # CanonicalTicket model & channel normalization
├── classification/           # Intent & urgency classification with calibrated scoring
├── routing/router.py         # Threshold gate & escalation decision logic
├── retrieval/store.py        # ChromaDB 0.3.21 wrapper & persistent index
├── generation/               # Citation-grounded generator & multi-tier fallback cascade
├── guardrails/               # PII scrubber & hallucination detection
└── audit/logger.py           # SQLite decision logger & metrics calculator
evaluation/harness.py         # Batch runner (--input, --output)
tests/                        # Pytest suite verifying A1 through A12
```

## Goals vs. Non-Goals

* **In-Scope Goals**:
  - Full satisfaction of all 12 acceptance criteria (A1–A12).
  - Ingestion across all 4 channels with robust schema normalization.
  - Calibrated routing with enriched escalation packets for human agents.
  - ChromaDB 0.3.21 retrieval with verifiable `[DOC-ID]` citations.
  - Active guardrails blocking PII and hallucinations via zero-tolerance human escalation.
  - Multi-tier fallback cascade terminating in a local offline heuristic mock.
  - Complete unattended batch evaluation CLI (`evaluation/harness.py`).
  - Unit and integration test suite (`pytest tests/ -v`).
* **Out-of-Scope Non-Goals**:
  - Live telephony / voice transcription.
  - Direct write-back integration to third-party proprietary ticketing platforms (Zendesk, Jira).
  - Autonomous customer account mutation or financial refunds without human authorization.
  - Multi-agent autonomous debate loops.

## Alternatives Weighed

* **LangChain / LlamaIndex vs. Lightweight Modular Pipeline**:
  - *Rejected*: Third-party agent frameworks introduce fragile abstractions, dependency bloat, and breaking API changes.
  - *Chosen*: Custom modular Python pipeline wrapping ChromaDB and provider SDKs directly.
* **Complete Retrieval Bypass vs. Enriched Escalation Packets**:
  - *Rejected*: Completely skipping retrieval on escalation deprives Tier 1 and Tier 2 agents of critical context, directly contradicting Daniel Okonkwo's interview requirements.
  - *Chosen*: Lightweight top-2 retrieval attached to escalation packets, while skipping expensive LLM generation and guardrail evaluation.
* **Recursive LLM Regeneration on Guardrail Failure vs. Zero-Tolerance Escalation**:
  - *Rejected*: Retrying after safety failures causes tail latency spikes and token waste. Marcus Adeyemi confirmed a wrong answer is the worst possible failure.
  - *Chosen*: Immediate diversion to the human escalation queue with diagnostic failure logs.

## Key Decisions & Staging for Next Steps

* **Decision 1**: Build the core pipeline as `src/orchestrator/engine.py` consumed identically by both `src/api.py` and `evaluation/harness.py`.
* **Decision 2**: Implement the enriched escalation hand-off packet (Intent, Urgency, Confidence, Routing Trigger Reason, Candidate Documentation Links) while skipping LLM generation.
* **Decision 3**: Enforce zero-tolerance escalation on PII or hallucination detection to honor the core stakeholder reliability mandate.
* **Decision 4**: Initialize ChromaDB via `chromadb.Client(Settings(...))` with persistent storage to comply with pinned dependency `chromadb==0.3.21`.
* **Decision 5**: Implement the 4-tier fallback cascade (Groq $\rightarrow$ Gemini $\rightarrow$ HF $\rightarrow$ Offline Mock) to guarantee zero-crash compliance.
