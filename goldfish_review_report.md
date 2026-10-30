# Goldfish Annotated Review Report

**Status:** resolved  
**Target:** `docs/designs/support_orchestrator.md` (`DetailedRange`: lines 541..764)

## Summary of Resolution Actions
*   **Total Findings**: 9
*   **Accepted / Applied Fixes**: 9
*   **Contested Items**: 0
*   **Escalated Items**: 0
*   **Declined Items**: 0
*   **Remaining Open Issues**: 0

All 9 findings have been applied directly to `docs/designs/support_orchestrator.md`. The Detailed Implementation Plan is fully structured into 6 sequential phases aligned with the 5-day milestone checkpoints, test infrastructure (`tests/conftest.py`) is specified, all files carry `[Create]` or `[Modify]` action tags, exact channel mappings and regex PII scanners are defined, and `run_id` is integrated into the state contract.

---

## Prioritized Findings & Applied Edits

### Finding 1: Absence of Incremental Phasing and Checkpoints [`egm-implementation-readiness`, `egm-codebase-details`]
* **Status**: FIXED
* **Resolution**: Replaced the flat 14-item file list with 6 structured phases:
  - Phase 1: Environment, Core Models, Ingestion & Inbound Sanitization (Day 1 Milestone)
  - Phase 2: Knowledge Base Chunking, Vector Storage & Traceable Retrieval (Day 2 Milestone)
  - Phase 3: Classification, Deterministic Routing & SQLite Audit Persistence (Day 3 Milestone)
  - Phase 4: Grounded Synthesis, Active Guardrails & 3-Tier Inference Cascade (Day 4 Milestone)
  - Phase 5: LangGraph StateGraph Assembly & FastAPI Web Service (Day 5 Milestone — Part 1)
  - Phase 6: Batch Evaluation CLI, Automated Metrics Report & Complete Test Suite (Day 5 Milestone — Part 2)

### Finding 2: Test Infrastructure & Mock Harness Neglect [`egm-codebase-details`, `egm-implementation-readiness`]
* **Status**: FIXED
* **Resolution**: Explicitly defined `tests/conftest.py` with mock HTTP transport fixtures (`httpx.MockTransport`), temporary in-memory ChromaDB fixtures, and synthetic ticket datasets.

### Finding 3: Unmarked Target File Actions [`egm-codebase-details`]
* **Status**: FIXED
* **Resolution**: Prefixed every target file across all 6 phases with explicit `[Create]` or `[Modify]` markers.

### Finding 4: Underspecified Channel Mapping and Cleaning Logic [`egm-implementation-readiness`]
* **Status**: FIXED
* **Resolution**: Documented exact field aliasing rules for email, chat, docs_comment, and forum, and defined text cleaning as whitespace collapsing and HTML tag stripping.

### Finding 5: Missing Prompts, Calibration, and Safety Veto Rules [`egm-implementation-readiness`]
* **Status**: FIXED
* **Resolution**: Documented JSON output schema, temperature 0.0 setting, and explicit regex trigger list for `must_not_auto_respond`.

### Finding 6: Ambiguous Chunking Thresholds & Idempotent Vector Store [`egm-implementation-readiness`]
* **Status**: FIXED
* **Resolution**: Documented collection name `cloudserve_kb`, exact character/word splitting thresholds, and idempotent startup check logic.

### Finding 7: Missing Gemini SDK, Runtime Dependencies, and Offline Heuristic Mapping [`egm-implementation-readiness`, `egm-codebase-details`]
* **Status**: FIXED
* **Resolution**: Added `uvicorn>=0.27.0`, `httpx>=0.26.0`, and `python-dotenv>=1.0.0` to requirements, specified `httpx` client transport for Gemini, and documented the offline keyword intent dictionary.

### Finding 8: Missing Inbound PII Scrubbing and State `run_id` Propagation [`egm-codebase-details`]
* **Status**: FIXED
* **Resolution**: Added inbound PII redaction during ingestion/normalization, and inserted `run_id` into the Pipeline State Contract table.

### Finding 9: Style & Parallelism Cleanup [`egm-style`]
* **Status**: FIXED
* **Resolution**: Standardized on imperative verbs across all task descriptions, added cross-platform shell activation commands, and removed the `*Drafted with EGM*` footer.
