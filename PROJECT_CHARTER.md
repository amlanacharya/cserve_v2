# CloudServe Solutions AI Support Capstone — Project Charter & Master Plan

## 1. Registered Facts & Directives
- **Target Deadline**: **November 8, 2026** (Accelerated 9-day full lifecycle execution).
- **Remote Git Repository**: [https://github.com/amlanacharya/cserve_v2](https://github.com/amlanacharya/cserve_v2)
- **Primary LLM Provider**: Groq API (`.env` verified and operational: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, and Llama-3.3 fallbacks).
- **Secondary/Fallback LLM Providers**: Google Gemini API, HuggingFace Inference API, and mock/offline fallbacks to ensure zero-crash resilience (A11).
- **Video Production & Recording**:
  - **HeyGen HyperFrames** ([github.com/heygen-com/hyperframes](https://github.com/heygen-com/hyperframes)): Code-driven HTML/CSS/GSAP video generation for slide cards, metrics visualizations, and structured narrative segments.
  - **Antigravity IDE**: Screen capture of live unattended batch runs, interactive ticket processing, escalation triggers, and guardrail blocking.
  - **Submission Video Requirements**: Exactly 18–22 minutes, 1080p MP4, user visible on intro/outro, $\ge 7$ minutes live software demo.
- **Expected Scope**: Complete end-to-end delivery of the entire project:
  - Working software satisfying all 12 Acceptance Criteria (A1–A12).
  - All 5 completed Stage Workbooks + Daily Effort Log.
  - Comprehensive 20–30 page Project Report (PDF).
  - 20-minute polished video presentation (`01_Video/`).
  - Final zipped submission package (`AmlanAcharya_Capstone_Submission.zip`).

---

## 2. The 12 Acceptance Criteria (A1 – A12)

| ID | Criterion | Verification & Gate Status |
|---|---|---|
| **A1** | Clean checkout launch | Starts from an empty directory using single documented README command. |
| **A2** | 4-channel ingestion | Ingests and normalises email, live chat, documentation comments, and community forum. |
| **A3** | Intent & urgency classification | Outputs class and calibrated confidence score $\in [0.0, 1.0]$. |
| **A4** | Grounded retrieval | Searches `05_Datasets/documentation.json` and returns verified passage citations. |
| **A5** | Deterministic routing | Data-calibrated threshold; identical ticket inputs produce identical routing decisions. |
| **A6** | Verifiable answer citations | Generated responses carry citations linking strictly to retrieved source text. |
| **A7** | Active guardrail blocking | At least one guardrail blocks responses on trigger (PII leakage, unsupported claims). |
| **A8** | Persistent decision log | Every single automated decision is logged with required schema and reconciles with ticket counts. |
| **A9** | Unattended evaluation run | Processes the full evaluation dataset unattended via `--input` and `--output` CLI flags. |
| **A10** | Automated metrics report | Automatically computes volume, business, technical, and governance metrics. |
| **A11** | Zero-crash fault tolerance | Handles model timeouts, provider disconnects, rate limits, and malformed data gracefully. |
| **A12** | Single-command test suite | `pytest tests/ -v` executes cleanly and passes all assertions. |

---

## 3. 6-Stage Delivery Plan

### Stage 1: Discovery & Evidence Analysis (Oct 30 – Oct 31)
- Ingest and parse the 5 stakeholder transcripts (`05_Datasets/Stakeholder_Interviews.docx`).
- Perform exploratory data analysis (EDA) across the 500 tickets in `05_Datasets/development_tickets.json`.
- Identify channel breakdown, resolution rates, document citation patterns, and discrepancy points.
- Formulate the core problem statement and complete `02_Stage_Workbooks/Stage_1_Discovery_Workbook.docx`.

### Stage 2: Product Requirements Document (PRD v1) (Oct 31 – Nov 1)
- Define user personas: Support Agents (Tier 1/2), Support Management, End Customers.
- Author functional requirements (FR1–FR10) and non-functional requirements (NFR1–NFR6) with strict traceability to Stage 1 discovery evidence.
- Complete `02_Stage_Workbooks/Stage_2_PRD_Template.docx`.

### Stage 3: Specifications & Prompt Library (Nov 1 – Nov 2)
- Formulate versioned prompts for:
  1. Multi-channel ticket normalisation.
  2. Intent & urgency classification with calibrated confidence.
  3. Retrieval query transformation.
  4. Response generation with strictly grounded citations.
  5. Escalation summarization for human engineering handoff.
  6. Guardrail validation (PII detection and hallucination check).
- Complete `02_Stage_Workbooks/Stage_3_Prompt_Library.docx`.

### Stage 4: Sprint Plan & Capacity Modeling (Nov 2)
- Capacity estimation and work breakdown structure (WBS).
- Sprint backlog with explicit definitions of done (DoD) and risk contingencies.
- Complete `02_Stage_Workbooks/Stage_4_Sprint_Plan.docx`.

### Stage 5: System Implementation & Unattended Evaluation (Nov 2 – Nov 5)
- **`src/` package development**:
  - `src/ingest/`: Channel normalisers for email, live chat, forum, doc comments.
  - `src/classify/`: Classifier utilizing Groq/Gemini with confidence scoring.
  - `src/retrieve/`: ChromaDB vector retrieval engine indexing `05_Datasets/documentation.json`.
  - `src/route/`: Deterministic routing decision engine with escalation bundling.
  - `src/generate/`: Citation-grounded answer generator.
  - `src/guardrails/`: PII scrubber and hallucination blocker.
  - `src/logging/`: Append-only SQLite/JSON decision logger.
  - `src/api.py`: FastAPI application serving REST endpoints.
- **Evaluation Harness**:
  - `evaluation/harness.py`: CLI taking `--input` and `--output`.
  - `evaluation/metrics.py`: Computes FCR, latency, precision/recall, escalation rate, guardrail activations.
- **Testing**:
  - `tests/`: Pytest suite verifying A1 through A12, including fault-injection tests (provider disconnect, malformed input).
- **PRD Revision**:
  - Complete `02_Stage_Workbooks/Stage_5_PRD_Revision_Log.docx` and author PRD v2.

### Stage 6: Final Deliverables Packaging (Nov 5 – Nov 7)
- **Report**: 20–30 page PDF (`AmlanAcharya_Capstone_Report.pdf`) following the 10-section structure.
- **Video**: 20-minute MP4 (`AmlanAcharya_Capstone_Video.mp4`) created with HyperFrames and Antigravity live demo recording.
- **Workbooks & Effort Log**: All 5 completed workbooks and `AmlanAcharya_Effort_Log.pdf`.
- **Git Push**: Push full codebase to `https://github.com/amlanacharya/cserve_v2`.
- **Final Archive**: Package everything into `AmlanAcharya_Capstone_Submission.zip` and verify checklist before November 8, 2026.

