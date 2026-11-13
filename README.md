# CloudServe Support Orchestrator

A support-ticket pipeline: it ingests tickets from four channels, redacts PII, classifies intent and urgency, retrieves knowledge-base passages, routes each ticket through two independent gates (classification confidence and retrieval similarity, plus safety vetoes), drafts a grounded answer with citations, checks the draft with a guardrail, and writes every decision to an append-only audit log. Tickets that fail any check go to a human with an escalation packet.

The design, evaluation and results are in `02_Report/AmlanAcharya_Capstone_Report.pdf`.

## Project layout

```
src/
  api.py            FastAPI app: dashboard, /tickets/process, /tickets/{id}/feedback, /health, decision log
  templates/        dashboard.html (the in-app demo UI)
  core/             Pydantic models, settings (.env), PII regex patterns
  ingest/           normalizer for email / chat / docs_comment / forum tickets, PII redaction
  classify/         intent + urgency classification, safety veto, classification cache
  retrieval/        header-based chunking and ChromaDB vector store (indexed on first use)
  routing/          dual-gate router, escalation packets, priority score
  generation/       provider cascade (OpenRouter, Gemini, offline), prompts, answer formatter
  guardrails/       PII and grounding (hallucination) checks on drafts
  audit/            append-only SQLite decision log (UPDATE/DELETE blocked by triggers)
  orchestrator/     LangGraph state graph tying the stages together
evaluation/         batch harness (harness.py), metrics (metrics.py), measured runs in results/
prompts/            versioned system prompts
tests/              unit and integration tests (150)
05_Datasets/        knowledge base, 500 development tickets, 80 validation tickets, ground truth
02_Report/          the report (PDF and Markdown source)
01_Video/           project_submission_full.mp4 and project_app_demo.mp4
presentation/       slide deck (open index.html)
.env.example        configuration template
```

## Set up

Requires Python 3.11.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
pip install -e .
copy .env.example .env            # macOS/Linux: cp .env.example .env
```

Edit `.env` and set at least one provider key. The recommended profile is OpenRouter with the larger model:

```
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL=openai/gpt-oss-120b
PROVIDER_ORDER=openrouter
```

`GEMINI_API_KEY` and `GROQ_API_KEY` are optional fallback tiers. With no key at all the system still runs: every ticket goes to a human (the offline tier never writes a customer answer). The first run downloads the embedding model and builds the vector index in `data/chromadb`.

Other settings worth knowing (all in `.env.example`): `RETRIEVAL_SIMILARITY_FLOOR` (0.40), `MAX_SPEND_USD` (abort a run past this OpenRouter spend), and `GUARDRAIL_RETRY=1` (opt-in "assisted" mode: one regenerate on a grounding failure, meant for use with a human reviewing replies; see report Section 7.10).

## Start the server

```bash
uvicorn src.api:app --port 8000
```

- Dashboard: http://localhost:8000/
- API docs: http://localhost:8000/docs
- Process a ticket: `POST /tickets/process` with a ticket JSON (see any entry in `05_Datasets/validation_tickets.json`)
- Health check: `GET /health`

Decisions are written to `data/decision_log.db`.

## Run the tests

```bash
pytest tests/ -q
```

## Run the evaluation

Unattended batch run over a ticket file, with metrics (first-contact resolution, calibration error, retrieval precision, latency percentiles) written to JSON:

```bash
python -m evaluation.harness --input 05_Datasets/validation_tickets.json --output evaluation/validation_report.json --delay 0.3
```

Use `05_Datasets/development_tickets.json` for the 500-ticket set. Past runs and their configurations are in `evaluation/results/` (`RUN_MANIFEST.md` lists them).
