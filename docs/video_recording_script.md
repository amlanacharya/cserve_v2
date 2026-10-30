# CloudServe Support Orchestrator — 20-Minute Video Recording Script & Runbook

*   **Presenter:** Amlan Acharya
*   **Video Target Length:** Exactly 18 to 22 minutes (Target: 19:30)
*   **Video Format:** 1080p MP4 (`AmlanAcharya_Capstone_Video.mp4`)
*   **Editing Plan:** Record terminal screencasts & HyperFrames slides in Antigravity / OBS, then use **Microsoft Clipchamp** to attach talking-head webcam video at the start (00:00–02:00) and close (18:00–20:00).

---

## Master Timeline & Visual Cues

| Timestamp | Visual Source | Speaker Section | Topic / Deliverable |
|---|---|---|---|
| **00:00 – 02:00** | **Webcam (Speaker on Camera)** | Section 1 | The Problem: CloudServe baseline (42% FCR), 70% repeat inquiries, senior burnout. |
| **02:00 – 05:00** | **HyperFrames (Slide 2)** | Section 2 | Discovery Evidence: 5 transcripts, 500 ticket EDA, vocabulary mismatch, escalation gap. |
| **05:00 – 07:00** | **HyperFrames (Slide 3)** | Section 3 | Architecture Walkthrough: Modular monolith, LangGraph StateGraph, dual gates, cascade. |
| **07:00 – 14:00** | **Terminal / IDE (Live Screencast)** | Section 4 | **Live Demonstration ($\ge 7$ min)**: Pytest suite, batch evaluation CLI, live API execution, 3 CUJs, fault injection. |
| **14:00 – 17:00** | **HyperFrames (Slide 5)** | Section 5 | Experimental Results: 68.3% FCR, 0.074 ECE calibration, P95 latency (870 ms), 100% audit log. |
| **17:00 – 18:00** | **HyperFrames (Slide 6)** | Section 6 | Governance & Risk: XML sandboxing, Luhn check PII scrubbing, append-only SQLite triggers. |
| **18:00 – 20:00** | **Webcam (Speaker on Camera)** | Section 7 | Economics & Rollout: $8.50 vs $0.003 unit cost, 3-phase rollout, conclusion. |

---

## Detailed Minute-by-Minute Script

### Part 1: The Problem (00:00 – 02:00)
**Visual:** Webcam video (Speaker clearly visible on camera, friendly and professional).  
*Clipchamp Splice Point: 00:00 – 02:00*

> "Hello everyone. My name is **Amlan Acharya**, and welcome to this capstone presentation of the **CloudServe Support Orchestrator**—a decoupled, modular AI processing pipeline built for automated first-contact resolution and fail-safe human escalation.
> 
> Let’s begin with the operational reality at CloudServe. CloudServe operates cloud infrastructure for thousands of enterprise customers. Over the last two quarters, customer support operations hit a major scaling wall:
> 
> 1. **First-Contact Resolution is stuck at 42%**, far below management’s 65% target.
> 2. **70% of all incoming tickets are repeat inquiries**—standard password lockouts, API key rotations, rate limits, and container rollback loops with already documented solutions.
> 3. **50% of tickets escalated to Tier 2 engineering should never have left Tier 1**. Escalations arrive without structured context, forcing senior infrastructure engineers to repeat basic discovery questions, blowing out resolution times to over 18 hours.
> 
> CloudServe needed more than a simple chatbot. They needed a verifiable, audit-compliant system that ingests multi-channel inquiries, grounds every answer in authoritative documentation, enforces strict safety guardrails, and provides enriched, structured escalation packets when human intervention is truly needed."

---

### Part 2: What Discovery Told Us (02:00 – 05:00)
**Visual:** Switch to **HyperFrames Presentation Slide 2** (`presentation/index.html`).

> "In Stage 1, we analyzed qualitative transcripts from five internal stakeholders—the VP of Customer Success, Tier 1 and Tier 2 leads, the Head of Product, and the Security Officer—and performed exploratory data analysis across 500 production development tickets.
> 
> Our findings reshaped the architecture around three core insights:
> 
> *   **First, Vocabulary Mismatch:** Customers rarely use internal terminology. A customer writes: *'my build keeps dying during health check,'* whereas the authoritative document is titled *'Resolving container health check failures'*. Standard keyword search completely breaks down under colloquial and non-fluent English. We concluded that **dense semantic retrieval using ChromaDB and all-MiniLM-L6-v2 embeddings** was non-negotiable.
> *   **Second, The Escalation Black Hole:** When Tier 1 agents escalate, they leave blank tickets or brief notes like *'needs help'*. Tier 2 engineers spend thirty minutes discovering what the customer is asking. Our system needed to build an automated, enriched **Escalation Packet** that attaches inferred intent, urgency, the routing failure reason, and the top-2 candidate documentation passages from retrieval cache.
> *   **Third, Zero-Tolerance Safety:** CloudServe cannot afford automated hallucinations, accidental refunds, or PII leaks. Production downtime inquiries must never wait in an automated retry queue, and account-deletion or refund requests must strictly divert to human agents."

---

### Part 3: System Architecture & Design (05:00 – 07:00)
**Visual:** Switch to **HyperFrames Presentation Slide 3** (`presentation/index.html`).

> "To deliver these requirements without distributed microservice overhead, we implemented the orchestrator as an in-process **Modular Monolith** coordinated by a **LangGraph StateGraph**.
> 
> Here is how a ticket flows:
> 
> 1.  **Ingestion:** The ticket enters through `src/ingest/normalizer.py`, normalizing four distinct channels (`email`, `chat`, `docs_comment`, `forum`) into a single `CanonicalTicket` schema while scrubbing inbound credentials and credit cards.
> 2.  **Classification:** `src/classify/classifier.py` classifies intent and urgency, producing a calibrated confidence score $c \in [0.0, 1.0]$ backed by a SHA-256 deterministic cache.
> 3.  **Grounded Retrieval:** In `src/retrieval/store.py`, ChromaDB queries the 29 documentation articles—chunked into 87 semantic header-based passages—returning cosine similarity $s_{\text{ret}}$. Notice this retrieval happens **before** routing.
> 4.  **Independent Dual-Gate Router:** In `src/routing/router.py`, the routing decision is a pure deterministic function. A ticket is routed to `AUTO_RESPOND` if and only if:
>     *   Intent confidence $c \ge 0.75$, **and**
>     *   Retrieval similarity $s_{\text{ret}} \ge 0.65$, **and**
>     *   Urgency is not `CRITICAL`, **and**
>     *   `must_not_auto_respond` is false.
>     The two scores are orthogonal and never blended.
> 5.  **Branch A (Auto-Respond):** `src/generation/generator.py` compiles XML-sandboxed prompts, invokes the model to cite exact `[DOC-ID]` anchors, and validates through active PII and hallucination guardrails.
> 6.  **Branch B (Escalation):** Ambiguous, critical, or guardrail-tripped tickets early-bypass generation, assemble an `EscalationPacket`, and proceed directly to audit.
> 7.  **Resilient 3-Tier Cascade & Fault Tolerance:** Powered by Groq, with fallback to Google Gemini, and a tertiary offline fail-safe mock. Every node is wrapped with `@safe_node`, guaranteeing zero unhandled process crashes."

---

### Part 4: Live Software Demonstration (07:00 – 14:00 &bull; $\ge 7$ MINUTES)
**Visual:** Screencast of Terminal (PowerShell) and IDE. Font size enlarged to 16pt+ for high legibility.

#### Step 4.1: Single-Command Test Suite (A12)
**Command:**
```powershell
.\.venv\Scripts\pytest tests/ -v
```
**Speaking Cue:**
> "Let us start by running our automated test suite. Acceptance Criterion A12 requires a single command to execute all tests.
> 
> As you can see, all 35 tests pass cleanly in under 12 seconds: covering 4-channel ingestion, chunking bounds (asserting 87 chunks), routing truth tables, PII and hallucination guardrails, SQLite append-only trigger enforcement, and fault-injection resilience."

#### Step 4.2: Unattended Batch Evaluation Run (A9 & A10)
**Command:**
```powershell
python -m evaluation.harness --input 05_Datasets/validation_tickets.json --output evaluation/validation_report.json --delay 0.5
```
**Speaking Cue:**
> "Now let us execute the batch evaluation CLI on the 120 production validation tickets. Criterion A9 requires this run to process unattended without human intervention.
> 
> The harness streams each ticket through the LangGraph pipeline, respecting our configurable delay to avoid provider rate limits.
> 
> Notice the real-time progress bar. The orchestrator is normalizing channels, executing dense ChromaDB vector search, evaluating dual gates, generating answers with citations, and logging every single decision to SQLite in WAL mode.
> 
> And there it completes! Let's examine the generated metrics summary:
> *   Total Processed: 120 of 120 (100% reconciliation).
> *   First-Contact Resolution Rate: 68.3%, successfully exceeding our 65% target.
> *   Expected Calibration Error: 0.074, well below the 0.15 ceiling.
> *   P95 Latency: 870 ms, well below the 3.0s SLA."

#### Step 4.3: Live Ticket Scenarios (API & Three CUJs)
**Command:**
```powershell
# Open interactive python or launch API
uvicorn src.api:app --port 8000
```
*(In a second terminal window or python script, execute the 3 critical scenarios):*

*   **Scenario 1 (CUJ 1: Grounded Auto-Resolution):**
    ```powershell
    Invoke-RestMethod -Uri http://localhost:8000/tickets/process -Method Post -ContentType "application/json" -Body '{"channel":"forum","ticket_id":"DEMO-01","post_title":"Need to rotate exposed API key","post_content":"One of our keys was exposed and returns 401. How do we rotate it?"}' | ConvertTo-Json -Depth 5
    ```
    **Speaking Cue:**
    > "In Scenario 1, a forum post asks about rotating an exposed key. The system ingests it, matches intent `api_key_issue` with high confidence, retrieves `DOC-AUTH-004`, and returns an automated response with citations: `[DOC-AUTH-004]`. Disposition is `AUTO_RESOLVED`."

*   **Scenario 2 (CUJ 2: Fail-Safe Escalation on Critical Urgency):**
    ```powershell
    Invoke-RestMethod -Uri http://localhost:8000/tickets/process -Method Post -ContentType "application/json" -Body '{"channel":"chat","ticket_id":"DEMO-02","message":"EMERGENCY: Production database is down! Complete outage for all users!"}' | ConvertTo-Json -Depth 5
    ```
    **Speaking Cue:**
    > "In Scenario 2, a customer reports production downtime. The router recognizes `CRITICAL` urgency. Notice what happens: generation is immediately bypassed, latency is under 200 ms, `final_disposition` is `ESCALATED_ROUTER`, and an `EscalationPacket` is created attaching the top-2 candidate documentation links."

*   **Scenario 3 (CUJ 3: Active Guardrail Tripping):**
    ```powershell
    Invoke-RestMethod -Uri http://localhost:8000/tickets/process -Method Post -ContentType "application/json" -Body '{"channel":"email","ticket_id":"DEMO-03","subject":"Payment update","body":"Here is my credit card 4532-0150-1234-5671 for the monthly bill."}' | ConvertTo-Json -Depth 5
    ```
    **Speaking Cue:**
    > "In Scenario 3, a ticket includes a credit card with valid Luhn checksum. Our inbound normalizer immediately sanitizes it to `[REDACTED_CC]`. If any draft response attempts to output customer PII or hallucinated claims, our post-generation guardrail suppresses delivery and diverts the ticket to `ESCALATED_GUARDRAIL`."

---

### Part 5: What the Numbers Say (14:00 – 17:00)
**Visual:** Switch to **HyperFrames Presentation Slide 5** (`presentation/index.html`).

> "Let us review our empirical results across the 120 validation tickets in detail:
> 
> *   **Business Outcome (FCR):** We achieved a **68.3% First-Contact Resolution rate**, surpassing CloudServe’s 65% target from a baseline of 42%. Over two-thirds of customer inquiries now receive an instant, citation-backed resolution without human touch.
> *   **Technical Calibration (ECE):** A common failure of LLM classifiers is overconfidence. We binned confidence into 10 intervals. Our **Expected Calibration Error is 0.074**, well under the 0.15 threshold. When the classifier reports 80% confidence, empirical accuracy is approximately 80%.
> *   **Latency Performance:** The 95th percentile latency across automated responses was **870 milliseconds**, comfortably beneath our 3.0-second SLA. Escalated tickets achieved a P95 latency of just 220 milliseconds because generation is bypassed.
> *   **Audit Reconciliation:** All 120 tickets were reconciled 1:1 in SQLite. Zero orphaned or dropped rows."

---

### Part 6: Governance, Security & Auditability (17:00 – 18:00)
**Visual:** Switch to **HyperFrames Presentation Slide 6** (`presentation/index.html`).

> "Let’s address governance and security—critical factors for enterprise adoption:
> 
> *   **Prompt Injection Sandboxing:** Customer text is escaped (`<` and `>` converted to HTML entities) and placed inside explicit XML boundaries (`<ticket_body>`). The system prompt instructs models that text inside tags is data, not instructions.
> *   **Dual-Stage PII Scrubbing:** We combine regex with Luhn checksum validation, scrubbing credit cards, phone numbers, email addresses, and CloudServe API keys pre-ingestion and post-generation.
> *   **Append-Only SQLite Decision Ledger:** Every routing step, similarity score, and disposition is recorded in `data/decision_log.db`. SQL triggers explicitly reject `UPDATE` and `DELETE` queries, ensuring an immutable audit trail for compliance officers."

---

### Part 7: Operational Economics, Roadmap & Conclusion (18:00 – 20:00)
**Visual:** Switch to **HyperFrames Presentation Slide 7**, then cut to **Webcam (Speaker on camera)** for closing.  
*Clipchamp Splice Point: 18:00 – 20:00*

> "Finally, let’s look at operational unit economics.
> 
> At CloudServe, an average Tier 1 human resolution costs approximately **$8.50**, factoring in an 18-minute handle time. In contrast, an automated resolution through our pipeline costs **less than $0.003** in token and compute costs.
> 
> At an inquiry volume of 10,000 tickets per month, achieving a 68% automated resolution rate saves CloudServe **over $55,000 every single month**, while reducing human queue wait times from 4 hours to seconds.
> 
> **Our Rollout Roadmap:**
> 1.  **Weeks 1–2 (Dark Launch):** The orchestrator runs in shadow mode behind production traffic, verifying decisions against human agent actions with zero write-back.
> 2.  **Weeks 3–4 (Conservative Canaries):** We enable auto-response for high-confidence ($\tau \ge 0.85, \sigma \ge 0.75$) billing and authentication inquiries on chat and forum channels.
> 3.  **Week 5+ (Full General Availability):** Broaden thresholds to $\tau=0.75, \sigma=0.65$ across all channels with ongoing feedback loops.
> 
> In conclusion, the CloudServe Support Orchestrator satisfies all twelve acceptance criteria, replaces repetitive human discovery with grounded AI resolution, and maintains strict safety guardrails.
> 
> Thank you for your time, and I look forward to your questions."

---

## Clipchamp Editing & Splicing Instructions

1.  **Record Webcam Video 1 (Intro):** Record yourself speaking **Part 1** (00:00 – 02:00) using your webcam or phone in 1080p.
2.  **Record Screencast 1 (Slides & Live Demo):** Record your screen playing **HyperFrames Slides 2 & 3**, then your terminal/IDE running **Part 4 (Live Demo)**, and **Slides 5, 6, & 7** (02:00 – 18:00).
3.  **Record Webcam Video 2 (Outro):** Record yourself speaking **Part 7 conclusion** (18:00 – 20:00).
4.  **In Clipchamp:**
    *   Create a 16:9 1080p project.
    *   Drop `Webcam_Intro.mp4` on Track 1.
    *   Drop `Screencast_Slides_and_Demo.mp4` immediately after it.
    *   Drop `Webcam_Outro.mp4` at the end.
    *   Apply a clean 0.5s cross-dissolve transition between clips.
    *   Export as `AmlanAcharya_Capstone_Video.mp4` at 1080p.

