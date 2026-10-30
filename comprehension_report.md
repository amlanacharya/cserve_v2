# Comprehension Test Report (Stage 6)

**Target Document:** `docs/designs/support_orchestrator.md`  
**Reviewer:** Naive Reader (`egm-comprehension`)  
**Scope:** `FeatureRange` (lines 1..312) & `DetailedRange` (lines 313..399)  
**Date:** 2026-10-31  

---

### What this proposes
The document proposes implementing the CloudServe Support Orchestrator as an in-process, modular monolith pipeline orchestrated via a LangGraph `StateGraph` to automate multi-channel customer inquiry handling while satisfying 12 acceptance criteria (A1–A12). Inbound tickets from four channels (`email`, `chat`, `docs_comment`, `forum`) are normalized into a canonical schema, classified for intent and urgency, and matched against 29 indexed knowledge base articles in ChromaDB using dense semantic embeddings (`all-MiniLM-L6-v2`). A dual-threshold gate routes tickets either to citation-grounded response generation or to an enriched human escalation packet based on classification confidence ($\tau \ge 0.75$), retrieval similarity ($\sigma \ge 0.65$), urgency level, and safety flags. Automated responses undergo active PII and hallucination guardrail checks before delivery, and all decisions are logged to an append-only SQLite database (`decision_log.db`). Resilience against crashes and outages (A11) is achieved through `@safe_node` exception wrappers and a 3-tier model provider fallback cascade (Groq $\rightarrow$ Google Gemini $\rightarrow$ Local Deterministic Offline Mock).

### How the existing system works, per this document
According to this document, CloudServe's current customer support operations rely on human agents who achieve a First-Contact Resolution (FCR) of only 42% against a 65% business target, with approximately 70% of inbound tickets being repetitive inquiries with known solutions. Support agents struggle to find answers in the 29 curated documentation articles because keyword searches fail on vocabulary mismatch and non-fluent customer phrasing. Consequently, 50% of tickets escalated from Tier 1 to Tier 2 could have been resolved at Tier 1, while existing escalations lack structured context and force senior engineers to repeat basic discovery. Additionally, manual operations carry trust and downtime risks due to inconsistent responses and a lack of verifiable source attribution.

---

### Audit Findings

#### 1. Undefined State Flag `must_not_auto_respond` in Routing Gate
* **Severity:** 🟡 Major
* **Affected Scope:** Section *Critical User Journeys (CUJs)*, Line 83; Section 5 *Unified Retrieval & Dual-Gate Routing Flow*, Line 241; Section 3 *Pipeline State Contract*, Lines 200–220.
* **Discrepancy Description & Rationale:**
  In CUJ 2 (Line 83) and in the mathematical routing formula (Line 241), the pipeline checks `must_not_auto_respond == true` / `\neg \text{must\_not\_auto\_respond}` to force escalation. However, `must_not_auto_respond` does not appear anywhere in the Pipeline State Contract table (Lines 200–220), nor is it defined as a field in `CanonicalTicket`, nor is there any node or rule explaining how or when it is set. A new developer implementing `src/routing/router.py` has no specification for where this condition originates.

#### 2. Missing Field Definitions for Core Data Models (`CanonicalTicket`, `DocumentChunk`, `EscalationPacket`, `ProcessedTicketResult`)
* **Severity:** 🟡 Major
* **Affected Scope:** Section 1 *Architectural Topology*, Line 100; Section 3 *Pipeline State Contract*, Lines 203, 207, 213; Section 2 *Target Files*, Line 323; Line 337.
* **Discrepancy Description & Rationale:**
  The document states that state channels are governed by explicit data contracts rather than low-level TypedDicts (Line 198), but it never defines the attributes, fields, or types for these models. Specifically:
  - `CanonicalTicket`: The document mentions subject, body, channel, and non-fluent normalization, but omits the exact schema and field names required.
  - `DocumentChunk`: Used as `list[DocumentChunk]` in retrieval state, but its model fields (chunk ID, doc ID, text content, similarity score metadata) are not specified anywhere in `src/core/models.py`.
  - `EscalationPacket`: The prose lists candidate links and routing reasons, but the concrete structure expected by downstream consumers or human agents is unspecified.
  - `ProcessedTicketResult`: Declared as a core model in Line 100 and Line 323, but never described in the state contract or architecture.

#### 3. Undefined Project Reference: "Stage 3" and Unlinked Document
* **Severity:** 🟡 Major
* **Affected Scope:** Section *Decisions & Rejected Alternatives*, Lines 290–292.
* **Discrepancy Description & Rationale:**
  Decision 5 states: *"Stage 3 requires a human-maintained prompt library with static version history ([Stage_3_Prompt_Library.docx](file:///c:/Users/amlan/Downloads/cloudserve/FDE_Capstone_Complete/Capstone_Pack/02_Stage_Workbooks/Stage_3_Prompt_Library.docx))."*
  For a reader new to the project, "Stage 3" is an unstated, undefined project division not introduced anywhere in this design document. Furthermore, referencing an external docx file without defining its role or integrating its contents into the architectural plan creates an unstated dependency on course/project workbook artifacts.

#### 4. Ambiguity Between Whole Document Indexing and Chunking Strategy
* **Severity:** 🟡 Major
* **Affected Scope:** Goals G3 (Line 28), Configuration Parameters (Lines 50–51), Section 5 (Line 239), Section *Decisions & Rejected Alternatives* (Line 287).
* **Discrepancy Description & Rationale:**
  There is conflicting terminology regarding how `05_Datasets/documentation.json` is processed:
  - Line 287 states: *"Embedding 29 passages using `all-MiniLM-L6-v2` completes in < 1.5 seconds on CPU,"* implying each of the 29 articles is indexed as a single passage without chunking.
  - Conversely, Lines 50, 51, 207, and 259 explicitly refer to "top retrieved article chunk", "$k_{\text{passages}} = 3$ Document Chunks", and "list[DocumentChunk]".
  If the 29 articles (which contain multi-section markdown guides) are split into chunks, the chunking strategy (token count, chunk size, chunk overlap, header splitting) is completely unstated. If they are not chunked, calling them "chunks" and referring to 29 passages contradicts standard retrieval terminology.

#### 5. Non-Existent Model Identifier (`openai/gpt-oss-120b`) on Groq and Unexplained `langchain-openai` Pin
* **Severity:** 🟡 Major
* **Affected Scope:** Section 6 *Streamlined 3-Tier Provider Cascade*, Line 248; Section 1 *Target Files*, Line 318.
* **Discrepancy Description & Rationale:**
  - Line 248 lists `openai/gpt-oss-120b` under the Primary Groq API tier (`llama-3.3-70b-versatile` / `openai/gpt-oss-120b`). Groq does not offer an `openai/gpt-oss-120b` model endpoint.
  - In the implementation plan (Line 318), the document specifies updating `openai>=1.10.0,<2.0.0` for `langchain-openai`. It is unexplained why `langchain-openai` is required when the stated provider tiers are Groq, Google Gemini, and Local Mock. If Groq is being accessed via the LangChain OpenAI-compatible base URL adapter rather than `langchain-groq`, this should be explicitly stated.

#### 6. Inconsistency in Graph Flow between Routing, Escalation, and Guardrails
* **Severity:** 🟡 Major
* **Affected Scope:** Mermaid Diagram (Lines 103–128), Critical User Journeys (Line 84), Section 10 *Detailed Implementation Plan* (Line 358).
* **Discrepancy Description & Rationale:**
  - In CUJ 2 (Line 84) and the Mermaid diagram (Lines 114–125), tickets routed to `ESCALATE` directly execute `EscBuilder` and bypass `generation` and `guardrails`, proceeding directly to `SQLiteLog`.
  - However, in Section 10 (Line 358), the implementation plan describes: *"LangGraph StateGraph compilation connecting Ingest $\rightarrow$ Classify $\rightarrow$ Retrieve $\rightarrow$ Route $\rightarrow$ Generate / Escalate $\rightarrow$ Guardrails $\rightarrow$ Audit."*
  This linear notation suggests that `Escalate` feeds into `Guardrails`, which contradicts the diagram and bypass logic. Additionally, the node names vary between the diagram (`EscBuilder`, `SQLiteLog`), the state contract (`escalate_node`), and the implementation files (`escalation.py`, `logger.py`).

#### 7. Vague Calculation of "Blended Confidence" vs Dual-Threshold Formula
* **Severity:** 🟡 Major
* **Affected Scope:** Section 6 *Provider-Independent Calibration*, Line 252; Section 5 *Dual-Gate Routing Logic*, Line 241.
* **Discrepancy Description & Rationale:**
  Line 252 claims: *"routing confidence blends model probability with semantic retrieval similarity ($s_{\text{ret}}$) and heuristic validation checks."*
  No equation or heuristic weighting rule is given for how this blending is calculated. Furthermore, in Section 5 (Line 241), the routing gate evaluates classification confidence $c \ge 0.75$ and top retrieval similarity $s_{\text{ret}} \ge 0.65$ as two independent gate variables. If $c$ already blends $s_{\text{ret}}$, the retrieval score is being evaluated twice without an explicit formula.

#### 8. Missing Concrete Schema for SQLite Decision Log (`decision_log.db`)
* **Severity:** 🟡 Major
* **Affected Scope:** Section 8 *Audit Logging*, Line 266; Section 9 *Target Files*, Line 352.
* **Discrepancy Description & Rationale:**
  While Line 266 lists summary fields captured in `data/decision_log.db`, no SQL DDL schema, column constraints, or data types are provided. Acceptance Criterion A8 requires verifying that decisions reconcile with all processed tickets. Key details—such as primary key structure, handling of timestamps, JSON serialization of metadata/citations, and audit reconciliation queries—are left unstated.

#### 9. Undefined Acronyms: "ECE" and "EGM"
* **Severity:** 🟢 Nit
* **Affected Scope:** Acceptance Criteria Table (Line 70), Section 8 (Line 267), Section 12 (Line 366), Line 399.
* **Discrepancy Description & Rationale:**
  - The metric "ECE" is introduced alongside FCR and latency without defining the acronym (Expected Calibration Error) or specifying its mathematical calculation or binning parameters.
  - The document footer notes `*Drafted with EGM*` without defining "EGM".

#### 10. Under-specified I/O Schema for Evaluation Batch CLI
* **Severity:** 🟢 Nit
* **Affected Scope:** Section 12 *Detailed Implementation Plan*, Line 365; Verification Plan, Line 392.
* **Discrepancy Description & Rationale:**
  The evaluation CLI `evaluation/harness.py` takes `--input` and `--output` flags, but the document does not define the input JSON schema (whether it matches `CanonicalTicket` or raw multi-channel formats) nor the exact JSON schema produced for `validation_report.json` (aggregate summary object vs list of scored records).

#### 11. Vague Specification for Tertiary Offline Heuristic Mock
* **Severity:** 🟢 Nit
* **Affected Scope:** Section 6, Line 250; Section 7, Line 345.
* **Discrepancy Description & Rationale:**
  The tertiary tier is described as a "Local Deterministic Heuristic Engine... Biased strictly towards safe escalation." It is unclear whether this mock ever synthesizes an automated answer via keyword extraction or if its sole behavior is deterministic fallback to escalation. Clarifying this contract will ensure predictable test assertions for Criterion A11.

