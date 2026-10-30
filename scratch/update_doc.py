import os

plan_text = """## Detailed Implementation Plan

The implementation is partitioned into six sequential, incremental phases aligned with the five-day build checkpoints in the Build Specification. Each phase leaves the codebase in a stable, buildable, and testable state verified by explicit test commands.

### Phase 1: Environment, Core Models, Ingestion & Inbound Sanitization (Day 1 Milestone)

*   **Objective**: Configure the Python 3.11 build environment, establish core Pydantic contracts, and implement multi-channel ingestion with inbound PII scrubbing.
*   **Target Files**:
    *   `[Modify] 06_Configuration/requirements.txt`: Update pinned dependencies to include `openai>=1.10.0,<2.0.0`, `langgraph>=0.0.26`, `chromadb==0.3.21`, `sentence-transformers>=2.2.2`, `sqlalchemy==2.0.0`, `fastapi>=0.109.0`, `uvicorn>=0.27.0`, `pydantic>=2.5.0`, `httpx>=0.26.0`, `python-dotenv>=1.0.0`, `pytest>=7.4.0`, and `pytest-asyncio>=0.23.0`.
    *   `[Create] pyproject.toml`: Configure editable package install for `src` using `setuptools` or `hatchling` under `uv`.
    *   `[Create] .env.example`: Template declaring `GROQ_API_KEY`, `GEMINI_API_KEY`, `GROQ_GEN_MODEL=llama-3.3-70b-versatile`, `GROQ_CLASSIFY_MODEL=llama-3.1-8b-instant`, `GEMINI_MODEL=gemini-2.5-flash`, and default thresholds.
    *   `[Create] src/__init__.py`: Package root marker.
    *   `[Create] src/core/__init__.py`: Export core models and settings.
    *   `[Create] src/core/config.py`: Implement centralized `Settings` loading environment variables with defaults for $\\tau = 0.75$, $\\sigma = 0.65$, timeouts, and retry parameters.
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
        *   Implement `query_documents(query_text: str, top_k: int = 3) -> list[DocumentChunk]`: query ChromaDB, convert cosine distance $d$ to similarity $s_{\\text{ret}} = 1 - d$, and return sorted chunks.
    *   `[Create] tests/unit/test_retrieval.py`: Test chunking output bounds (70–90 chunks), metadata preservation (`doc_id`), and similarity scoring against sample queries.
*   **Checkpoint Gate (Day 2)**:
    ```bash
    pytest tests/unit/test_retrieval.py -v
    ```
    Asserts that all 29 articles are indexed, chunk counts fall in 70–90, and top retrieved passages match expected ground truth articles with $s_{\\text{ret}} \\ge 0.65$ (A4).

---

### Phase 3: Classification, Deterministic Routing & SQLite Audit Persistence (Day 3 Milestone)

*   **Objective**: Implement intent and urgency classification, deterministic dual-gate routing, and append-only SQLite decision logging.
*   **Target Files**:
    *   `[Create] src/classify/__init__.py`: Export `classify_ticket`.
    *   `[Create] src/classify/cache.py`: In-memory and file-backed deterministic cache keyed on `sha256(canonical_ticket_json)` (A5).
    *   `[Create] src/classify/classifier.py`: Query Groq `llama-3.1-8b-instant` (temperature 0.0) with static prompt requesting JSON output:
        ```json
        {
          "inferred_intent": "billing | authentication | deployment_failure | rate_limiting | general_inquiry",
          "intent_alternatives": {"<intent>": <score>},
          "urgency": "LOW | MEDIUM | HIGH | CRITICAL",
          "confidence": <float between 0.0 and 1.0>
        }
        ```
        Evaluate safety veto: set `must_not_auto_respond = True` if inquiry matches regex `(refund|billing\\s+adjustment|delete\\s+my\\s+account|legal\\s+action|attorney|subpoena|security\\s+vulnerability|breach|exploit|talk\\s+to\\s+a\\s+human|agent)`.
    *   `[Create] src/routing/__init__.py`: Export `evaluate_route` and `build_escalation_packet`.
    *   `[Create] src/routing/router.py`: Pure-function routing gate evaluating independent criteria:
        $$\\text{Action} = \\begin{cases} \\text{AUTO\\_RESPOND} & \\text{if } c \\ge 0.75 \\land s_{\\text{ret}} \\ge 0.65 \\land \\text{urgency} \\neq \\text{CRITICAL} \\land \\neg \\text{must\\_not\\_auto\\_respond} \\\\ \\text{ESCALATE} & \\text{otherwise} \\end{cases}$$
        Generate detailed `routing_reason` articulating every passing and failing condition.
    *   `[Create] src/routing/escalation.py`: Implement `EscalationBuilder` assembling `EscalationPacket` using top-2 retrieved candidate chunks from state.
    *   `[Create] src/audit/__init__.py`: Export `log_decision` and `get_decision_history`.
    *   `[Create] src/audit/logger.py`: Implement append-only SQLite logger for `data/decision_log.db` matching Section 6.5 DDL:
        *   Execute `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;`.
        *   Install triggers prohibiting `UPDATE` and `DELETE`.
        *   Implement `log_decision(record: dict) -> None`.
    *   `[Create] tests/unit/test_classify.py`, `tests/unit/test_routing.py`, `tests/unit/test_audit.py`: Test classification parsing, full routing truth table (all combinations of $c$, $s_{\\text{ret}}$, urgency, and safety flags), and SQLite append-only triggers.
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
        *   Retry logic: Exponential backoff with full jitter on HTTP 429 ($b_0 = 1.0\\text{s}$, $b_{\\max} = 8.0\\text{s}$, max 1 retry).
        *   Tier 3 (Tertiary Offline Mock): Local Deterministic Heuristic Engine. Matches keywords to intent (`billing`, `auth`, `deploy`, `rate_limit`, `general`), retrieves local ChromaDB chunks, sets `must_not_auto_respond = True`, routes to `ESCALATE`, and never generates draft responses.
    *   `[Create] src/generation/generator.py`: Orchestrate prompt compilation, cascade query, and citation extraction.
    *   `[Create] src/guardrails/__init__.py`: Export `evaluate_guardrails`.
    *   `[Create] src/guardrails/pii.py`: Scan drafts for email, phone, bearer tokens, API keys, and credit cards with Luhn checksum validation.
    *   `[Create] src/guardrails/hallucination.py`: Validate citation integrity:
        1. All cited `[DOC-ID]`s exist in retrieved context.
        2. Unigram lexical entailment ratio between answer sentences and cited context $\\ge 0.5$.
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
        *   `normalize_node` $\\rightarrow$ `classify_node` $\\rightarrow$ `retrieval_node` $\\rightarrow$ `routing_node`.
        *   Conditional routing edge: `AUTO_RESPOND` $\\rightarrow$ `generation_node`; `ESCALATE` $\\rightarrow$ `escalate_node`.
        *   `generation_node` conditional edge: if draft generated $\\rightarrow$ `guardrails_node`; if provider failed $\\rightarrow$ `escalate_node`.
        *   `guardrails_node` conditional edge: `PASSED` $\\rightarrow$ `audit_node`; `TRIPPED` $\\rightarrow$ `escalate_node`.
        *   `escalate_node` $\\rightarrow$ `audit_node` $\\rightarrow$ `END`.
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
.venv\\Scripts\\activate
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
Verifies batch completion across all 120 validation tickets, confirming:
1. `validation_report.json` and `metrics_summary.csv` are generated.
2. Volume metrics reconcile: `total_processed == len(validation_tickets)`.
3. Business metrics achieve FCR target $\\ge 65\\%$.
4. Calibration metrics report ECE $\\le 0.15$.
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
"""

with open('docs/designs/support_orchestrator.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Normalize CRLF / LF for splitting
content_unified = content.replace('\r\n', '\n')

# Check run_id insertion
if '| `run_id` | `str`' not in content_unified:
    target_needle = '| State Key | Type Contract | Producing Node | Invariant / Description |\n|---|---|---|---|\n| `raw_ticket`'
    replacement = '| State Key | Type Contract | Producing Node | Invariant / Description |\n|---|---|---|---|\n| `run_id` | `str` | Input | Unique run identifier for batch execution or API session audit reconciliation. |\n| `raw_ticket`'
    if target_needle in content_unified:
        content_unified = content_unified.replace(target_needle, replacement, 1)
        print('Inserted run_id into State Contract')
    else:
        print('Could not find target_needle for run_id')

# Split at ## Detailed Implementation Plan
marker = '## Detailed Implementation Plan'
split_idx = content_unified.find(marker)
if split_idx != -1:
    base_content = content_unified[:split_idx]
    final_content = base_content + plan_text
    # Write back with CRLF
    with open('docs/designs/support_orchestrator.md', 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(final_content)
    print(f'Successfully updated docs/designs/support_orchestrator.md ({len(final_content.splitlines())} lines)')
else:
    print('Marker ## Detailed Implementation Plan not found')

