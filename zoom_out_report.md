# Initial Zoom Out Review Report (Stage 5 — Re-Audit)

**Target Document:** `docs/designs/support_orchestrator.md`  
**Reviewer:** Skeptical Architect (`egm-zoom-out`)  
**Standard:** Zoom Out Standard (`resources/document_standards/zoom-out-standard.md`)  
**Status:** Conditionally Approved (0 Blockers, 3 Major, 3 Nits)  
**Date:** 2026-10-31  

---

## Executive Summary

The revised design document represents a substantial improvement in architectural clarity and altitude control. It successfully resolves previous structural blockers by establishing a single LangGraph orchestration engine, unifying retrieval prior to routing, pruning provider cascade tiers from 4 to 3, designating SQLite as the authoritative audit store, and defining an explicit state contract table.

The remaining issues center on YAGNI cleanup (removing speculative MLflow tracking and redundant CLI scaffolding), resolving a data-flow contradiction regarding confidence blending vs. dual-gate routing, and consolidating minor file fragmentations.

---

## Detailed Findings

### Finding 1: Speculative MLflow Tracking & Architectural Contradiction
* **Severity:** 🟡 Major
* **Affected Scope:** Section *Goals* (lines 34–35), *Architectural Topology & Modular Monolith Pattern* (lines 127–128), *Streamlined Directory Scaffolding* (line 180), *Audit Logging & Optional Evaluation Tracking* (lines 268–269), *Decisions & Rejected Alternatives* (lines 278–281), and *Detailed Implementation Plan* (line 367).
* **Simplicity Rationale:** 
  The document formally rejects external observability daemons in Non-Goal NG6 and in Rejected Alternatives #2 ("Rejection of Distributed Tracing & Daemon-Based Observability"). However, it simultaneously introduces `evaluation/tracker.py`, an optional `--track` CLI flag, and an MLflow node in the Mermaid diagram. Furthermore, `mlflow` is not declared in `06_Configuration/requirements.txt`. SQLite (`decision_log.db`) and local evaluation reports (`evaluation/metrics.py`) already satisfy 100% of Acceptance Criteria A8, A9, and A10. Retaining MLflow as an "optional hook" adds speculative dead code and violates Zoom-Out Standard §2 (YAGNI).
  *Recommendation*: Fully purge MLflow references and `evaluation/tracker.py`. Keep local SQLite and JSON/CSV metric outputs as the sole evaluation deliverables.

---

### Finding 2: Redundant CLI Entrypoint (`src/cli.py`)
* **Severity:** 🟡 Major
* **Affected Scope:** Section *Streamlined Directory Scaffolding* (line 140), *Target Files to Create/Modify* (lines 361–363).
* **Simplicity Rationale:** 
  The Build Specification (Section 04, lines 327–339) defines exactly three operational interfaces: `src.api` (FastAPI REST service), `evaluation.harness` (unattended batch evaluation CLI), and `pytest tests/` (test suite). Introducing a standalone `src/cli.py` for "interactive and single-ticket processing" adds speculative interface duplication and maintenance overhead. Single-ticket verification is already served via `src/api.py` endpoints, unit tests, or by passing a 1-ticket JSON file to `evaluation.harness`.
  *Recommendation*: Eliminate `src/cli.py` to keep the public execution surface minimal and aligned with the project specification.

---

### Finding 3: Conflicting Definitions of Routing Confidence ($c$ vs. Blended Score)
* **Severity:** 🟡 Major
* **Affected Scope:** Section *Streamlined 3-Tier Provider Cascade & Calibration* (lines 251–252) vs. *Pipeline State Contract* (lines 206–209) and *Unified Retrieval & Dual-Gate Routing Flow* (line 241).
* **Simplicity Rationale:** 
  Line 241 specifies the dual-gate routing invariant cleanly:
  $$\text{Action} = \text{AUTO\_RESPOND} \iff c \ge \tau \ (0.75) \land s_{\text{ret}} \ge \sigma \ (0.65) \land \text{urgency} \neq \text{CRITICAL} \land \neg \text{must\_not\_auto\_respond}$$
  where $c$ is classification confidence from `classify_node` and $s_{\text{ret}}$ is retrieval similarity from `retrieval_node`.
  However, line 252 states that *"routing confidence blends model probability with semantic retrieval similarity ($s_{\text{ret}}$) and heuristic validation checks."* If retrieval similarity is blended into classification confidence prior to routing, evaluating $s_{\text{ret}} \ge \sigma$ at the routing gate double-counts the retrieval score and blurs the clean separation of concerns.
  *Recommendation*: Remove the blending language from line 252. Keep classification confidence $c$ strictly focused on intent/urgency certainty, and let the dual-gate router evaluate $c$ and $s_{\text{ret}}$ as independent, orthogonal conditions.

---

### Finding 4: Misplaced & Fragmented Caching Module (`src/classify/cache.py`)
* **Severity:** 🟢 Nit
* **Affected Scope:** Section *Streamlined Directory Scaffolding* (line 151), *Detailed Implementation Plan* (lines 331–333).
* **Simplicity Rationale:** 
  The directory scaffolding isolates `cache.py` inside `src/classify/`. However, response caching during development (encouraged in Build Specification §07 to conserve API quotas and guarantee reproducibility) is equally or more critical for `src/generation/generator.py`, which incurs significantly higher token usage. Isolating a cache module in `classify/` either leads to duplicate caching logic in `generation/` or over-specializes a general concern.
  *Recommendation*: Move caching to a lightweight shared helper (`src/core/cache.py`) or keep an in-memory/file dict directly inside the provider client without dedicating an isolated file under `classify/`.

---

### Finding 5: Mermaid Diagram Data-Flow Inconsistency
* **Severity:** 🟢 Nit
* **Affected Scope:** Section *Architectural Topology & Modular Monolith Pattern* (Mermaid diagram, lines 108–111).
* **Simplicity Rationale:** 
  The Mermaid diagram illustrates `Canon --> Classify --> CanonRet[Query String & Metadata] --> Retrieve`. This implies that `TicketClassifier` generates the query string and metadata consumed by ChromaDB retrieval. In contrast, the State Contract table (lines 201–209) and Section 5 (line 239) correctly specify that retrieval queries ChromaDB using the combined subject and normalized inquiry text directly from `CanonicalTicket`.
  *Recommendation*: Update the Mermaid diagram so that `Canon` feeds directly into both `Classify` and `Retrieve`, with both outputs joining at `RouteGate`.

---

### Finding 6: Indirection & File Sprawl in `src/orchestrator/`
* **Severity:** 🟢 Nit
* **Affected Scope:** Section *Streamlined Directory Scaffolding* (lines 170–175).
* **Simplicity Rationale:** 
  `src/orchestrator/` is fractured across four files: `state.py`, `graph.py`, `nodes.py`, and `wrappers.py`. `wrappers.py` contains only a 20-line `@safe_node` decorator, and `state.py` defines a single TypedDict schema. For an in-process modular monolith, this creates unnecessary navigation indirection.
  *Recommendation*: Consolidate `@safe_node` into `nodes.py` (or `wrappers.py` into `graph.py`), keeping the orchestration package lean.

---

### Conclusion

The document passes the core Zoom Out criteria: the root problem is front and center, the operational topology is simple and unified, and all 12 acceptance criteria have crisp traceability. Addressing the three Major items (dropping MLflow entirely, removing `src/cli.py`, and clarifying orthogonal calibration) will finalize this architecture as an airtight, minimal specification.
