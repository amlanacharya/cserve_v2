# Implementation Readiness Test Report (Stage 9)

**Target Document:** `docs/designs/support_orchestrator.md`  
**Review Scope:** `DetailedRange` (lines 541..625)  
**Reviewers:** 
- `egm-implementation-readiness` (Pragmatic Tech Lead)
- `egm-codebase-details` (Pedantic Technical Quality Auditor)
- `egm-style` (Technical Copy Editor)  
**Standard:** Implementation Readiness Standard (`implementation-readiness-standard.md`)  
**Date:** 2026-10-31  

---

## Executive Summary

The Implementation Readiness Test evaluated lines 541..625 (Detailed Implementation Plan and Verification Plan) of `docs/designs/support_orchestrator.md`. The reviewers identified critical compliance gaps against the **Zero-Decision Rule** and **Phasing & Checkpoints** mandates.

- **Blockers (2)**: 
  1. Complete absence of sequential phasing and intermediate verification checkpoints (violating the Build Specification 5-day milestone checkpoints).
  2. Complete omission of test infrastructure, shared fixtures, mock transports, and test harnesses (`tests/conftest.py`, network failure mocks).
- **Majors (8)**:
  1. Unmarked file actions (`[Create]`, `[Modify]`, `[Delete]`).
  2. Underspecified channel aliasing and text cleaning in `normalizer.py`.
  3. Missing prompt templates, calibration mapping, and concrete `must_not_auto_respond` keyword lists in `src/classify/`.
  4. Ambiguous chunk token thresholds and missing ChromaDB persistence initialization details.
  5. Missing Gemini client SDK, runtime packages (`uvicorn`, `httpx`, `python-dotenv`), and offline keyword dictionary in `src/generation/`.
  6. Lack of inbound PII scrubbing in the StateGraph topology.
  7. Missing `run_id` state channel propagation between entrypoints and the SQLite logger.
  8. Grammatical voice breakdowns across task items.
- **Nits (6)**: Unspecified REST API request/response types in task description, platform-coupled Windows activation script, pleonastic regex phrasing, telegraphic clauses, and footer metadata.

---

## Consolidated Findings

### Category: Implementation Readiness & Tech Lead (`egm-implementation-readiness`)

#### Finding IR-1: Absence of Incremental Phasing and Build Checkpoints
* **Severity:** 🔴 Blocker
* **Affected Scope:** Lines 541–602.
* **Finding & Guidance:**
  The plan is an unsequenced flat inventory of 14 file groups lacking execution phases, dependency ordering, and intermediate verification gates. It ignores the standard-mandated day-by-day build checkpoints in the Build Specification (Day 1: Ingest normalization, Day 2: Documentation retrieval, Day 3: Intent/Urgency classification and routing log, Day 4: Cited generation & guardrail trip, Day 5: Unattended batch run).
  *Remediation*: Restructure into 6 phased milestones with explicit entry criteria, file modifications, and testable checkpoint commands.

#### Finding IR-2: Underspecified Channel Mapping and Cleaning Logic in `normalizer.py`
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 554–557.
* **Finding & Guidance:**
  Field aliasing rules for the four channels (`email`, `chat`, `docs_comment`, `forum`) and the definition of non-fluent text cleaning are omitted.
  *Remediation*: Explicitly map raw fields (e.g. `raw_body`, `message`, `post_content`, `comment_text` to `body`; `from`, `user_id` to `sender_ref`) and define text normalization as whitespace collapsing and HTML tag stripping without altering phrasing.

#### Finding IR-3: Missing Classification Prompts, Calibration Extraction, and Safety Flag Rules
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 558–561.
* **Finding & Guidance:**
  The prompt template, system instructions, confidence parsing mechanism, and definitive keyword trigger list for `must_not_auto_respond` (e.g., refund, account deletion, security incident) are omitted.
  *Remediation*: Document the exact JSON schema, prompt template, and safety veto keyword dictionary.

#### Finding IR-4: Ambiguous Splitting Rules and Store Initialization
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 562–566.
* **Finding & Guidance:**
  Exact token thresholds (~256 and ~40 tokens), heading extraction rules, ChromaDB collection name (`cloudserve_kb`), and initialization idempotency are not defined.
  *Remediation*: Document deterministic splitting parameters and idempotent startup indexing.

#### Finding IR-5: Missing Fallback Heuristics, Prompt Sandbox Template, and Gemini SDK
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 571–575.
* **Finding & Guidance:**
  The keyword mapping dictionary for the offline fail-safe mock, the exact XML prompt template in `prompts.py`, and the client transport for Google Gemini (`google-generativeai` vs raw HTTP via `httpx`) are left unstated.
  *Remediation*: Provide the keyword intent mapping table, explicit Gemini client adapter using `httpx`, and complete prompt templates.

#### Finding IR-6: Unspecified Guardrail Detection Patterns and Entailment Overlap Thresholds
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 576–579.
* **Finding & Guidance:**
  The plan lacks exact regex patterns for PII scanning and a concrete mathematical metric/threshold for token-overlap entailment verification.
  *Remediation*: Specify regex definitions (email, phone, credit card Luhn check, API keys) and exact lexical unigram containment threshold ($\ge 0.5$).

#### Finding IR-7: Missing REST API Request/Response Schemas in `src/api.py`
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 588–590.
* **Finding & Guidance:**
  Input payload schema, HTTP methods (`POST`), status codes, and response envelopes for `/health` and `/tickets/process` are unstated in the task description.
  *Remediation*: Specify HTTP POST `/tickets/process` taking `raw_payload: dict` and returning `ProcessedTicketResult`.

#### Finding IR-8: Underspecified Evaluation Report Schema and Concrete Test Assertions
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 591–598, 604–622.
* **Finding & Guidance:**
  ECE bin count ($M=10$), report JSON top-level keys, and specific test function names are left abstract.
  *Remediation*: Specify evaluation JSON schema, CSV column format, and explicit test function names in the test plan.

---

### Category: Codebase Details & Quality Audit (`egm-codebase-details`)

#### Finding CD-1: Unmarked Target File Actions
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 543–601.
* **Finding & Guidance:**
  Files are listed without `[Create]`, `[Modify]`, or `[Delete]` tags. `06_Configuration/requirements.txt` already exists (`[Modify]`), while all other targets must be tagged `[Create]`.
  *Remediation*: Tag every file with its concrete action.

#### Finding CD-2: Test Infrastructure & Mock Harness Neglect
* **Severity:** 🔴 Blocker (Corroborates IR-1)
* **Affected Scope:** Lines 595–598, 620.
* **Finding & Guidance:**
  Validating A11 fault tolerance requires simulating network disconnects, HTTP 429 backoff, and model timeout failovers. The plan documents zero test infrastructure (`tests/conftest.py`, HTTP transport mocks, ephemeral ChromaDB fixture).
  *Remediation*: Add `tests/conftest.py` with mock HTTP transport fixtures and temporary vector store harnesses to the implementation tasks.

#### Finding CD-3: Missing Runtime and Gemini Dependencies
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 545–548.
* **Finding & Guidance:**
  Dependencies omit `uvicorn` (required for FastAPI), `httpx` (for Gemini client and test client), and `python-dotenv`.
  *Remediation*: Explicitly include `uvicorn>=0.27.0`, `httpx>=0.26.0`, and `python-dotenv>=1.0.0` in `requirements.txt`.

#### Finding CD-4: Omission of `.env.example` and Package `__init__.py` Files
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 543–601.
* **Finding & Guidance:**
  `.env.example` does not exist in the root and is omitted from target files. Package `__init__.py` files are not listed, risking import resolution failures under `pip install -e .`.
  *Remediation*: Add `.env.example` and all module `__init__.py` files to the target list.

#### Finding CD-5: Missing `run_id` in Orchestrator State Contract
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 583–586, 621.
* **Finding & Guidance:**
  `run_id` is an indexed primary column in SQLite, but is omitted from pipeline state channels and graph initialization.
  *Remediation*: Add `run_id: str` to state channels and graph input dictionaries.

#### Finding CD-6: Missing Inbound PII Scrubbing in StateGraph Topology
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 583–586 vs Line 462.
* **Finding & Guidance:**
  Graph topology runs guardrails only post-generation on auto-responses, allowing raw customer PII to enter classification prompts and SQLite logs unscrubbed.
  *Remediation*: Add inbound customer PII redaction during ingestion/normalization before classification.

#### Finding CD-7: Evaluation Output Path Ambiguity
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 591–594, 618.
* **Finding & Guidance:**
  `evaluation/harness.py` must support both file paths (`--output evaluation/validation_report.json`) and directory paths (`--output evaluation/results/`) to prevent failures during automated grading.
  *Remediation*: Handle both file and directory output paths in `evaluation/harness.py`.

---

### Category: Style & Technical Tone (`egm-style`)

#### Finding STY-1: Grammatical Parallelism Breakdown in Task Lists
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 554–601.
* **Style Rationale:**
  Tasks alternate between imperative verbs, bare noun phrases, and telegraphic fragments.
  *Remediation*: Standardize all task bullet points to use strong imperative verbs (*"Implement..."*, *"Expose..."*, *"Configure..."*).

#### Finding STY-2: Imprecise Retrieval Return Description
* **Severity:** 🟡 Major
* **Affected Scope:** Lines 563, 565.
* **Style Rationale:**
  Replace "size split" with "fixed-token length splitting", and clarify that `query_documents` returns candidate chunks ranked and annotated by cosine similarity.

#### Finding STY-3: Platform-Coupled Shell Syntax
* **Severity:** 🟡 Major
* **Affected Scope:** Line 609.
* **Style Rationale:**
  Line 609 uses Windows-only `.venv\Scripts\activate`.
  *Remediation*: Use cross-platform syntax (`source .venv/bin/activate` / `.venv\Scripts\activate`) or direct `uv run` commands.

#### Finding STY-4: Minor Pleonasm, Shorthand, and Non-Technical Footer
* **Severity:** 🟢 Nit
* **Affected Scope:** Lines 569, 577, 581, 585, 589, 625.
* **Style Rationale:**
  Simplify "Regex and pattern-based" to "Regex-based", replace informal shorthand ("docs", "top-2"), write complete sentences for logger tasks, and remove the non-technical footer `*Drafted with EGM*`.

