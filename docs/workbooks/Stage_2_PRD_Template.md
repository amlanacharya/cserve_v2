# Stage 2: Product Requirements Document (PRD v1 / v2)

**Author:** Amlan Acharya  
**Project:** CloudServe Support Orchestrator  
**Status:** Approved for Implementation & Evaluation (v2.0)  
**Date:** October 31, 2026  

---

## 1. Executive Summary & Problem Framing
CloudServe customer support operations suffer from an artificially depressed First-Contact Resolution rate of 42% (target 65%) and an average resolution time of 18.4 hours, driven not by lack of documentation but by vocabulary mismatch that blinds keyword search, and an unstructured escalation pipeline that forces senior engineers to repeat basic discovery on routine tickets. The solution requires a decoupled modular monolith combining multi-channel ingestion, dense semantic retrieval over 29 curated articles, independent dual-gate routing (confidence $\ge 0.75$, similarity $\ge 0.65$), citation-grounded answer generation, active guardrail blocking, and enriched escalation packaging.

---

## 2. User Groups & Personas

| User Persona | Core Needs | Current Workaround | Success Metric |
|---|---|---|---|
| **Customers Raising Tickets** | Instant, accurate, citation-backed answers for routine operational questions; immediate human handoff for production-critical outages. | Wait in generic queues for 4 to 18 hours or repeatedly re-submit tickets across channels. | FCR uplift to $\ge 65\%$, P95 latency $\le 3$ s on auto-responses, CSAT $\ge 4.2$. |
| **Tier 1 Support Agents** | Automated deflection of routine repeat tickets (API keys, lockouts, rollbacks) so they can focus on complex customer inquiries. | Manually search fragmented wikis while racing against strict 10-minute queue SLA clocks. | Routine ticket volume deflected by $65\%+$; handle time reduced by $50\%$. |
| **Tier 2 Senior Engineers** | Enriched escalation packets containing inferred intent, confidence, failed gate reasons, and top candidate documentation links. | Receive blank "needs help" tickets and repeat basic discovery questions from scratch. | Zero repeat discovery required; preventable escalations reduced by $50\%$. |
| **Head of Support (Marcus)** | Measurable FCR uplift, compliant append-only decision logging, and zero-tolerance brand safety protection. | Manually spot-checks tickets and defends poor SLA numbers to executive leadership. | Automated daily metrics reports (FCR, latency, ECE) and 100% audit reconciliation. |

---

## 3. Functional Requirements (FR)

| ID | Requirement Statement | Priority | Discovery Evidence | Acceptance Criteria |
|---|---|---|---|---|
| **FR-01** | The system shall ingest raw tickets from `email`, `chat`, `docs_comment`, and `forum` into a unified `CanonicalTicket` schema. | Must | Section 2 (EDA channel distribution) | 100% parse rate without validation exceptions across all channels (A2). |
| **FR-02** | The system shall scrub inbound PII (API keys `cs_live_...`, credit cards with Luhn check, phone, email, Bearer tokens) before state storage. | Must | Stakeholder interview: Security Officer | Zero unredacted credentials stored in SQLite or passed to models (A2). |
| **FR-03** | The system shall classify intent into 20+ classes, assess urgency, and output a calibrated confidence score $c \in [0.0, 1.0]$. | Must | Section 1 (Stakeholder transcripts) | ECE $\le 0.15$ across 10 bins; safety veto regex sets `must_not_auto_respond` (A3). |
| **FR-04** | The system shall chunk 29 documentation articles into 70–90 semantic passages and index them in ChromaDB using cosine distance. | Must | Section 1 (Vocabulary mismatch analysis) | Returns top-$k$ passages with cosine similarity $s_{\text{ret}} \in [0.0, 1.0]$ in $< 100$ ms (A4). |
| **FR-05** | The system shall evaluate independent orthogonal gates: auto-respond only when $c \ge 0.75$, $s_{\text{ret}} \ge 0.65$, urgency $\neq$ CRITICAL, and safe. | Must | Section 2 (Disagreement on auto-response safety) | Pure deterministic function with zero score blending; full explanation in audit reason (A5). |
| **FR-06** | The system shall synthesize responses grounded strictly in retrieved passages and cite valid `[DOC-ID]` source anchors. | Must | Stakeholder interview: Daniel Okonkwo | Every procedural claim cites valid document ID; XML delimiter sandboxing applied (A6). |
| **FR-07** | The system shall actively scan outgoing drafts and suppress delivery if PII leaks or ungrounded claims are detected. | Must | Section 2 (CSAT drop on hallucinations) | Tripped drafts diverted to `ESCALATED_GUARDRAIL` with violation metadata (A7). |
| **FR-08** | The system shall assemble an `EscalationPacket` attaching intent, confidence, urgency, routing reason, and top-2 candidate KB links. | Must | Section 1 (Escalation black hole) | Attached to 100% of escalated tickets; zero repeat discovery required by Tier 2. |
| **FR-09** | The system shall log every single decision to an append-only SQLite `decision_log` table with immutability triggers. | Must | Stakeholder interview: Security Officer | 100% ticket reconciliation; direct UPDATE and DELETE queries fail (A8). |
| **FR-10** | The system shall provide an unattended batch evaluation CLI supporting `--input`, `--output`, and `--delay`. | Must | Section 4 (Build specification) | Unattended completion over full validation dataset producing JSON & CSV reports (A9, A10). |

---

## 4. Non-Functional Requirements (NFR)

| ID | Requirement Statement | Target Metric | Architectural Enforcement |
|---|---|---|---|
| **NFR-01** | End-to-end response latency | P95 $\le 3,000$ ms for auto-responses; $\le 500$ ms for escalations | In-process modular monolith; early bypass of generation on escalations. |
| **NFR-02** | Fault tolerance & uptime | Zero process crashes across evaluation batches | `@safe_node` exception containment; 3-tier cascade (Groq $\rightarrow$ Gemini $\rightarrow$ offline mock) (A11). |
| **NFR-03** | Test suite execution | Single-command full coverage | `pytest tests/ -v` passing all 35 assertions in $< 15$ seconds (A12). |
| **NFR-04** | Local data sovereignty | Zero external database or server daemons | Local embedded ChromaDB (DuckDB/Parquet) and SQLite WAL persistence. |

