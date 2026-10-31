# CloudServe Support Orchestrator

## Overview

The **CloudServe Support Orchestrator** is a decoupled, modular monolith processing pipeline designed for enterprise customer support operations. It ingests multi-channel customer inquiries, classifies intent and urgency, retrieves grounded knowledge base passages from 29 curated documentation articles using ChromaDB, routes tickets through independent dual gates (intent confidence and retrieval similarity), synthesizes citation-backed answers with strict source anchors (`[DOC-ID]`), and enforces active safety guardrails against PII leakage and hallucination.

The system is coordinated by a LangGraph `StateGraph`, wrapped with `@safe_node` fault-tolerant exception containment, backed by an append-only SQLite decision audit log, and powered by a resilient 3-tier provider cascade (Groq $\rightarrow$ Google Gemini $\rightarrow$ offline fail-safe escalation engine).

---

## Acceptance Criteria Traceability (A1–A12)

| Criterion | Requirement Description | Architectural Component / File |
|---|---|---|
| **A1** | Clean checkout launch | `06_Configuration/requirements.txt`, `pyproject.toml`, and `.env.example`. |
| **A2** | 4-channel ingestion | `src/ingest/normalizer.py` parsing `email`, `chat`, `docs_comment`, and `forum`. |
| **A3** | Intent & urgency classification | `src/classify/classifier.py` emitting intent, intent alternatives, urgency, and confidence. |
| **A4** | Grounded retrieval | `src/retrieval/store.py` querying ChromaDB over header-chunked `05_Datasets/documentation.json`. |
| **A5** | Deterministic routing | `src/routing/router.py` evaluating independent orthogonal gates ($c \ge 0.75$, $s_{\text{ret}} \ge 0.65$). |
| **A6** | Verifiable answer citations | `src/generation/generator.py` enforcing strictly grounded `[DOC-ID]` citations. |
| **A7** | Active guardrail blocking | `src/guardrails/` (`pii.py`, `hallucination.py`) suppressing tripped drafts and diverting to escalation. |
| **A8** | Persistent decision log | `src/audit/logger.py` append-only SQLite `decision_log` table reconciling 100% of processed tickets. |
| **A9** | Unattended evaluation run | `evaluation/harness.py` batch CLI taking `--input`, `--output`, and `--delay`. |
| **A10** | Automated metrics report | `evaluation/metrics.py` computing volume, business (FCR), technical (latency, ECE), and governance metrics. |
| **A11** | Fault-tolerant execution | `@safe_node` wrappers on all nodes plus 3-tier cascade (Groq $\rightarrow$ Gemini $\rightarrow$ offline mock). |
| **A12** | Single-command test suite | `pytest tests/ -v` covering unit modules, graph failure recovery, and end-to-end flows. |

---

## Quickstart & Installation (A1)

### 1. Environment Setup
```bash
# Create and activate Python 3.11 virtual environment using uv
uv venv --python 3.11
.venv\Scripts\activate   # On Windows
# source .venv/bin/activate # On Unix/macOS

# Install dependencies and editable package
uv pip install -r 06_Configuration/requirements.txt
uv pip install -e .
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and provide your API keys:
```bash
cp .env.example .env
```
Key variables:
- `GROQ_API_KEY`: Groq API key.
- `GEMINI_API_KEY`: Google Gemini API key.
- `INTENT_CONFIDENCE_THRESHOLD`: Minimum confidence $\tau = 0.75$.
- `RETRIEVAL_SIMILARITY_FLOOR`: Minimum similarity $\sigma = 0.65$.

---

## Running Verification Tests (A12)

Run the complete test suite across unit modules, integration flows, and resilience tests:
```bash
pytest tests/ -v
```

To run individual test stages:
```bash
# Day 1: Ingestion & PII Normalization (A2)
pytest tests/unit/test_ingest.py -v

# Day 2: Knowledge Base Chunking & Retrieval (A4)
pytest tests/unit/test_retrieval.py -v

# Day 3: Classification, Routing & SQLite Audit Logging (A3, A5, A8)
pytest tests/unit/test_classify.py tests/unit/test_routing.py tests/unit/test_audit.py -v

# Day 4: Grounded Synthesis, Guardrails & Cascade (A6, A7, A11)
pytest tests/unit/test_generation.py tests/unit/test_guardrails.py -v

# Day 5: LangGraph Orchestration & Resilience (A8, A11)
pytest tests/integration/test_orchestrator.py tests/integration/test_resilience.py tests/integration/test_audit_log.py -v
```

---

## Unattended Batch Evaluation CLI (A9 & A10)

Execute unattended batch evaluation across the validation dataset:
```bash
python -m evaluation.harness --input 05_Datasets/validation_tickets.json --output evaluation/validation_report.json --delay 1.5
```

This generates:
- `evaluation/validation_report.json`: Detailed hierarchical JSON report with volume, business, technical, and governance metrics.
- `evaluation/metrics_summary.csv`: Tabular CSV metrics summary.
- Appends reconciled rows to SQLite at `data/decision_log.db`.

---

## Running the REST API Service

Launch the FastAPI web service:
```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints:
- `GET /health`: Health check endpoint (`{"status": "ok"}`).
- `POST /tickets/process`: Ingest and process a raw JSON ticket payload, returning `ProcessedTicketResult`.
