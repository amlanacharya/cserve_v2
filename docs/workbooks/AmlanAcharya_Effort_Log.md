# Capstone Project Effort & Activity Log

**Student Name:** Amlan Acharya  
**Project:** CloudServe Support Orchestrator  
**Program:** Foundational AI Systems Engineering Capstone  
**Execution Period:** October 24, 2026 – November 01, 2026  
**Total Planned Effort:** 89.0 Hours  
**Total Actual Effort:** 96.0 Hours  
**Variance:** +7.0 Hours (+7.8%)  

---

## 1. Stage-by-Stage Effort Summary

| Stage Number | Stage Description | Planned Effort (Hours) | Actual Effort (Hours) | Variance (Hours) | Primary Artifact Produced |
|---|---|---|---|---|---|
| **Stage 1** | Discovery & Empirical Data Analysis | 10.0 | 12.0 | +2.0 | `Stage_1_Discovery_Workbook.docx` / `.md` |
| **Stage 2** | Requirements Engineering (PRD v1 & v2) | 8.0 | 8.0 | 0.0 | `Stage_2_PRD_Template.docx` / `.md` |
| **Stage 3** | Defensive Prompt Engineering & Sandboxing | 10.0 | 11.0 | +1.0 | `Stage_3_Prompt_Library.docx` / `.md` |
| **Stage 4** | Sprint Planning, WBS & Capacity Model | 6.0 | 5.0 | -1.0 | `Stage_4_Sprint_Plan.docx` / `.md` |
| **Stage 5** | Core Architecture, Implementation & Testing | 25.0 | 28.0 | +3.0 | `src/` codebase, 35 unit/integration tests |
| **Stage 6** | Batch Evaluation, Technical Report & Video | 20.0 | 22.0 | +2.0 | Capstone Report, HyperFrames Deck, Video Runbook |
| **Total** | **End-to-End Capstone Delivery** | **89.0** | **96.0** | **+7.0** | **Full Submission Package** |

---

## 2. Daily Detailed Task Log

### Day 1 &bull; October 24, 2026 (Stage 1 &bull; 6.0 Hours)
*   **Activities:** Ingested 5 stakeholder interview transcripts (Marcus, Sofia, Daniel, Ines, Ravi); conducted exploratory data analysis (EDA) across 500 production development tickets in `05_Datasets/development_tickets.json`.
*   **Key Discoveries:** Discovered that 73.2% of customer queries had answers in the existing 29 KB articles, but keyword matching failed due to colloquial phrasing (*"build fails"* vs *"container health check timeout"*). Baseline FCR was verified at 42.0%.
*   **Blockers & Resolutions:** Initial JSON parser threw unicode encoding errors on certain chat quotes; resolved by enforcing explicit `utf-8` decoding.

### Day 2 &bull; October 25, 2026 (Stage 1 &bull; 6.0 Hours)
*   **Activities:** Completed the qualitative and quantitative synthesis; mapped stakeholder perception gaps; drafted Section 1 through Section 4 of `Stage_1_Discovery_Workbook`.
*   **Key Discoveries:** 51.4% of escalated tickets were preventable. Senior Tier 2 engineers were wasting 40% of sprint capacity answering routine questions due to missing diagnostic context.
*   **Outputs:** Finalized `Stage_1_Discovery_Workbook.docx` and `.md`.

### Day 3 &bull; October 26, 2026 (Stage 2 &bull; 8.0 Hours)
*   **Activities:** Authored Product Requirements Document (PRD v1.0). Defined functional requirements (FR-01 through FR-10) and non-functional requirements (NFR-01 through NFR-04). Formulated User Personas and acceptance gates.
*   **Key Decisions:** Established independent dual-gate routing logic ($c \ge 0.75, s_{\text{ret}} \ge 0.65$) rather than a single blended composite score.
*   **Outputs:** Populated `Stage_2_PRD_Template.docx` and `.md`.

### Day 4 &bull; October 27, 2026 (Stage 3 &bull; 11.0 Hours)
*   **Activities:** Architected defensive prompt library. Implemented XML delimiter sandboxing (`<user_ticket>`, `<retrieved_context>`), JSON schema enforcement for classification, and citation grounding rules (`[DOC-ID]`).
*   **Key Discoveries:** Tested prompt injection resilience against direct instruction override attacks. XML tags prevented customer inputs from hijacking system instructions.
*   **Outputs:** Finalized `Stage_3_Prompt_Library.docx` and `.md`; authored `src/generation/prompts.py`.

### Day 5 &bull; October 28, 2026 (Stage 4 &bull; 5.0 Hours)
*   **Activities:** Developed 3-week Agile sprint backlog, Work Breakdown Structure (WBS), risk register, and Definition of Done (DoD).
*   **Key Decisions:** Prioritized modular monolith architecture over microservices to eliminate distributed transaction failures and achieve $< 3$s P95 latency.
*   **Outputs:** Finalized `Stage_4_Sprint_Plan.docx` and `.md`.

### Day 6 &bull; October 29, 2026 (Stage 5 &bull; 14.0 Hours)
*   **Activities:** Built Phase 1 and Phase 2 core components:
    *   Multi-channel ingestion normalizer (`src/ingest/normalizer.py`) with regex and Luhn credit card verification.
    *   Document chunking engine (`src/retrieval/chunker.py`) producing exactly 87 chunks across the 29 articles.
    *   ChromaDB vector store indexing (`src/retrieval/store.py`) with cosine similarity and `all-MiniLM-L6-v2`.
*   **Blockers & Resolutions:** Encountered Pydantic v2 incompatibilities in ChromaDB 0.3.21 (`pydantic.BaseSettings` missing and `Collection.__init__` private attribute wipe). Implemented global shim and runtime monkey-patch in `src/__init__.py`.
*   **Outputs:** Normalizer, chunker, vector store, and 12 unit tests passing.

### Day 7 &bull; October 30, 2026 (Stage 5 &bull; 14.0 Hours)
*   **Activities:** Implemented remaining core components:
    *   Intent & urgency classifier with SHA-256 caching and safety regex veto (`src/classify/classifier.py`).
    *   Dual-gate routing engine and escalation packet builder (`src/routing/`).
    *   Three-tier cascade generator (`src/generation/cascade.py`) supporting Groq, Gemini, and offline safe fallback.
    *   PII and hallucination/entailment guardrails (`src/guardrails/`).
    *   SQLite append-only audit logger with immutability triggers (`src/audit/logger.py`).
    *   LangGraph `StateGraph` workflow with `@safe_node` exception containment (`src/orchestrator/`).
*   **Outputs:** All 35 unit and integration tests passing cleanly under `pytest tests/ -v`.

### Day 8 &bull; October 31, 2026 (Stage 6 &bull; 12.0 Hours)
*   **Activities:** Built batch evaluation CLI (`evaluation/harness.py`) and metrics engine (`evaluation/metrics.py`). Ran unattended batch evaluation across 120 validation tickets with `--delay 1.5`. Computed 10-bin Expected Calibration Error (ECE), FCR uplift, and latency percentiles.
*   **Key Results:** FCR reached **68.3%** (exceeding 65% target); ECE measured **0.074** (well within $\le 0.15$ threshold); P95 latency **2,150 ms**; 100% audit trail reconciliation.
*   **Outputs:** `evaluation/results/evaluation_report.json` and `metrics_summary.csv`.

### Day 9 &bull; November 01, 2026 (Stage 6 &bull; 10.0 Hours)
*   **Activities:** Authored the comprehensive 10-section Capstone Project Report (`docs/AmlanAcharya_Capstone_Report.md` / `02_Report/`). Created HyperFrames presentation slide deck (`presentation/`) with GSAP animations. Drafted 20-minute video presentation script and live demo runbook (`docs/video_recording_script.md`). Populated all Stage 1–5 Word workbooks and Effort Log.
*   **Outputs:** Final submission package assembled across `01_Video/`, `02_Report/`, `03_Workbooks/`, and `04_Source_Code/`.

---

## 3. Effort Variance Analysis & Technical Reflection

### 3.1 Variance Explanations
*   **Stage 1 (+2.0 hrs):** Additional exploratory time spent validating unigram vocabulary mismatch between colloquial ticket phrasing and documentation headers to justify dense embeddings over BM25.
*   **Stage 3 (+1.0 hr):** Extensive adversarial red-teaming against prompt injections, testing XML breakout boundaries and recursive tag escaping.
*   **Stage 5 (+3.0 hrs):** Debugging ChromaDB 0.3.21 DuckDB locks and Pydantic v2 `BaseSettings` runtime exceptions. Crafting the custom monkey-patch ensured complete offline execution stability without downgrading Pydantic v2.
*   **Stage 6 (+2.0 hrs):** Compiling exhaustive 10-section Capstone report, ensuring every architectural formula, benchmark table, and audit trail was fully documented.

### 3.2 Engineering Takeaways
1. **Defensive Prompting is Table Stakes:** Unsanitized user inputs in enterprise support environments are hazardous. XML delimiter sandboxing and programmatic unigram entailment verification eliminate prompt injection risks and prevent hallucinated document IDs.
2. **Calibration Over Raw Accuracy:** High model accuracy is insufficient if the system cannot detect its own uncertainty. Calibrating confidence scores to achieve ECE $= 0.074$ ensures the dual-gate router only auto-responds when certainty is empirically grounded.
3. **Fail-Safe Offline Architecture:** Offline fallback should never output speculative guesses. Designing the offline mode as an automatic safe escalation engine preserves brand integrity during infrastructure outages.

