# CloudServe Support Orchestrator — Director's 18-Minute Master Narration Script

**Film Title:** Engineering a Decoupled Modular Monolith for Enterprise Support Orchestration  
**Director & Engineer:** Amlan Acharya  
**Target Duration:** Exactly 18 Minutes (1,080 Seconds / 32,400 Frames at 30 fps)  
**Format:** HyperFrames Deterministic HTML5 Video Composition  

---

## Directorial Pacing & Timeline Master Map

```text
[0:00 - 2:30 | 150s]  ACT I:   The Support Crisis, Vocabulary Mismatch & 500-Ticket Discovery
[2:30 - 5:00 | 150s]  ACT II:  The Architectural Thesis: Decoupled Modular Monolith vs Microservices
[5:00 - 7:30 | 150s]  ACT III: Multi-Channel Normalization, Ingestion & Algorithmic PII Scrubbing
[7:30 - 10:00| 150s]  ACT IV:  Bounded Semantic Chunking (87 Chunks) & ChromaDB Dense Retrieval
[10:00-12:30| 150s]  ACT V:   Independent Orthogonal Dual Gates & 3-Tier Cascade Sandboxing
[12:30-16:00| 210s]  ACT VI:  HERO PRODUCT DEMO — Live Pytest, FastAPI Endpoints, SQLite & Batch CLI
[16:00-18:00| 120s]  ACT VII: Measured Results (23.8% validation FCR, 44.2% dev-500 FCR, ECE 0.093), Honest Retrospective
TOTAL: Exactly 1,080 Seconds (18 Minutes)
```

---

## Act I: The Enterprise Support Crisis & Empirical Discovery (0:00 – 2:30 / 150s)

*   **Timeline:** `data-start="0"` &bull; `data-duration="150"`
*   **Visual Setup:** High-contrast crisis dashboard. The left card flashes the red metric `42.0% FCR` against the executive target `65.0%`. Center pane displays the 500-ticket exploratory data analysis (EDA) chart. Right pane animates the stakeholder conflict matrix.
*   **Voiceover Narration:**
    > *(0:00 – 0:35)* "Welcome. CloudServe's support function is under strain. More than five hundred tickets arrive each week across four channels, replies take eight to twelve hours against a two-hour agreement, and first-contact resolution is about 42 per cent against a 65 per cent target. The request was for a chatbot. I want to show you why that was the wrong frame. On screen, the left card shows that 42 per cent against the target, and the centre chart summarises the ticket analysis."
    > 
    > *(0:35 – 1:15)* "I interviewed five people. Marcus, the Head of Support, wants the easy tickets answered so his team can do the hard ones, and above all does not want a confidently wrong answer sent. Sofia, a tier-one agent, says seven in ten tickets repeat and that the documentation is fine, she just cannot find things in it. Daniel, in tier two, says escalations arrive with no context. Ines, who writes the knowledge base, says search matches titles, not customer wording. The panel on the right maps where these views conflict."
    > 
    > *(1:15 – 1:55)* "I tested those claims on the 500 development tickets. 71.4 per cent are answerable from the 29 articles, which supports Sofia: the answers exist. Historical FCR is 43.8 per cent and mean resolution time about seven hours. Daniel thought half of escalations were avoidable; the data says 92 of 281, about a third. So the disagreement is real, but smaller than he thought. The chart in the centre breaks the 500 tickets down by whether the documentation already holds the answer. That is the evidence behind everything that follows."
    > 
    > *(1:55 – 2:30)* "Put together, this is a findability and handoff problem, not a content problem. It calls for retrieval before generation, a safe human route for anything uncertain, escalations that carry their working, and a decision record a compliance reviewer can read. Let's look at the architecture. Four requirements follow from that. Retrieve before generating. Send anything uncertain to a person. Make every escalation carry its working. And record every decision in a log that a reviewer can read."

---

## Act II: The Architectural Thesis: Decoupled Modular Monolith (2:30 – 5:00 / 150s)

*   **Timeline:** `data-start="150"` &bull; `data-duration="150"`
*   **Visual Setup:** Clean Architecture hexagonal blueprints. Nodes pulse sequentially: `Domain Models` &rarr; `Ingestion` &rarr; `Retrieval` &rarr; `Classification` &rarr; `Routing` &rarr; `Generation` &rarr; `Guardrails` &rarr; `Audit Logger`. A comparison table contrasts Modular Monolith vs Distributed Microservices.
*   **Voiceover Narration:**
    > *(2:30 – 3:10)* "When designing mission-critical AI systems, the industry's default reflex is often distributed microservices: one service for classification, another for retrieval, a third for generation, and an external broker for messages. In our architectural design phase, we explicitly rejected microservices in favor of a Decoupled Modular Monolith. Why? Because support orchestration is an inherently synchronous, latency-critical, stateful decision pipeline. Think of it as one process with clear internal boundaries, rather than many processes joined by a network."
    > 
    > *(3:10 – 3:50)* "Microservices introduce network serialization overhead, cold-start latency, distributed transaction failure modes, and operational deployment bloat. Under our P95 latency constraint of sub-3 seconds for auto-responses and sub-500 milliseconds for escalations, every millisecond counts. By packaging our domain modules within a single cohesive Python process—governed by Clean Architecture principles and strict Pydantic v2 data contracts—we achieve zero network overhead between pipeline stages while maintaining pristine module isolation."
    > 
    > *(3:50 – 4:30)* "At the core of the orchestrator lies our domain contract layer in `src/core/models.py`. Inbound requests are parsed into an immutable `CanonicalTicket`. Retrieved documents are encapsulated in `DocumentChunk` records. Routing decisions materialize as pure, deterministic records, and any ticket diverted from auto-response is packaged into an enriched `EscalationPacket`. On screen, the nodes light up in the order a ticket travels: models, ingestion, retrieval, classification, routing, generation, guardrails and audit."
    > 
    > *(4:30 – 5:00)* "To orchestrate these components without brittle spaghetti code, we implemented a LangGraph `StateGraph` workflow. Each node in the graph is wrapped in our custom `@safe_node` decorator. If an external API experiences a network partition, the decorator catches the exception, encapsulates the error into ticket metadata, and cleanly diverts execution to safe human escalation—preventing any unhandled process crash. Let's inspect the ingestion pipeline."

---

## Act III: Multi-Channel Normalization & Cryptographic PII Scrubbing (5:00 – 7:30 / 150s)

*   **Timeline:** `data-start="300"` &bull; `data-duration="150"`
*   **Visual Setup:** Side-by-side data transformation interface. On the left, raw inbound inputs from Chat, Email, Forum, and Doc Comments. On the right, the scrubbed, standardized `CanonicalTicket`. Regex scanners and Luhn checksum algorithms highlight and redact credentials in real time.
*   **Voiceover Narration:**
    > *(5:00 – 5:40)* "CloudServe tickets arrive across four heterogeneous channels, each with its own quirks and formatting idiosyncrasies. Email tickets carry forward headers and quoted signatures. Chat tickets arrive as fragmented, colloquial strings. Forum threads feature nested markdown and code snippets, while documentation comments arrive anchored to specific page URLs. Our `TicketNormalizer` in `src/ingest/normalizer.py` ingests these raw payloads and maps them into a unified `CanonicalTicket` schema with 100% type safety."
    > 
    > *(5:40 – 6:25)* "Crucially, customer support tickets are a frequent vector for accidental credential exposure. Developers frequently paste raw API keys, private tokens, phone numbers, and even payment cards when seeking help. Passing unredacted credentials to third-party LLM providers violates GDPR, SOC-2, and PCI-DSS compliance mandates. We implemented a two-stage active scrubbing engine: First, deterministic anchored regexes match CloudServe API keys (`cs_live_...`) and standard Bearer tokens, replacing them with cryptographic redaction markers."
    > 
    > *(6:25 – 7:05)* "Second, for financial credentials, naive 16-digit regexes produce catastrophic false positives on ticket IDs, timestamps, and UUIDs. To solve this, our scrubber implements the Luhn checksum algorithm. Every 13-to-19 digit numerical candidate is subjected to mod-10 doubling and checksum verification. Only valid Visa, Mastercard, and Amex numbers are redacted. Non-financial sequences are preserved intact. On the right of the screen you can watch a candidate number pass or fail the checksum, and only the valid card is redacted."
    > 
    > *(7:05 – 7:30)* "This ensures that zero raw credentials ever touch our vector store, our LLM prompts, or our persistent SQLite decision logs. Once normalized and sanitized, the ticket proceeds to semantic retrieval. What you see on the right is the clean ticket, with the key and card replaced by markers."

---

## Act IV: Bounded Semantic Chunking & Dense ChromaDB Retrieval (7:30 – 10:00 / 150s)

*   **Timeline:** `data-start="450"` &bull; `data-duration="150"`
*   **Visual Setup:** Knowledge base chunking visualizer. 29 markdown articles decompose into exactly 87 semantic passages. A 2D scatter plot demonstrates the dense embedding space generated by `sentence-transformers/all-MiniLM-L6-v2` inside ChromaDB.
*   **Voiceover Narration:**
    > *(7:30 – 8:15)* "To overcome the vocabulary mismatch that paralyzed keyword search, we built a semantic retrieval engine powered by dense vector embeddings. CloudServe's knowledge base comprises 29 curated operational articles. A common blunder in naive RAG pipelines is arbitrary fixed-token chunking—splitting text every 500 characters, which slices code blocks and troubleshooting steps in half. Instead, our `MarkdownChunker` in `src/retrieval/chunker.py` performs document-aware parsing anchored to H2 and H3 markdown headers. The visualiser on screen shows the twenty-nine articles breaking apart into passages along their headings."
    > 
    > *(8:15 – 9:00)* "Each chunk captures an isolated, self-contained operational procedure—such as 'Root Cause Analysis', 'Resolution Steps', or 'Prerequisites'. By merging small trailing subsections under 40 words into their parent resolution headers, our chunker produces exactly 87 semantic passages across the 29 articles—landing squarely within our strict architectural target of 70 to 90 chunks. Every chunk is assigned a deterministic identifier formatted as document ID followed by chunk index, preserving complete provenance. Keeping provenance on every chunk is what later lets a citation be checked against the exact passage."
    > 
    > *(9:00 – 9:40)* "These 87 passages are embedded using `sentence-transformers/all-MiniLM-L6-v2` and indexed inside an embedded ChromaDB 0.3.21 instance backed by local DuckDB and Parquet files in `data/chromadb`. During retrieval, the normalized ticket query is embedded and evaluated against the index using cosine distance, which we transform into a normalized similarity score $s_{\text{ret}} \in [0.0, 1.0]$. The scatter plot shows those passages as points, and passages about the same problem sit close together."
    > 
    > *(9:40 – 10:00)* "Because dense retrieval maps concepts into semantic embedding space rather than exact characters, queries like 'service keeps getting killed' match 'Container OOMKilled Troubleshooting' with a cosine similarity of 0.88 in under 45 milliseconds! Now, how do we decide whether to auto-respond?"

---

## Act V: Independent Orthogonal Dual Gates & Cascade Generator (10:00 – 12:30 / 150s)

*   **Timeline:** `data-start="600"` &bull; `data-duration="150"`
*   **Visual Setup:** Interactive Dual-Gate decision matrix. Gate 1: Classification Confidence $c \ge 0.75$. Gate 2: Semantic Similarity $s_{\text{ret}} \ge 0.65$. Urgent/Veto checks. XML prompt sandboxing diagram and 3-Tier fallback cascade (Groq &rarr; Gemini &rarr; Safe Mock).
*   **Voiceover Narration:**
    > *(10:00 – 10:45)* "In PRD v1.0, the preliminary proposal was to use a blended composite score: $S = 0.5c + 0.5s_{\text{ret}} \ge 0.70$. During empirical testing, we proved this formula was fundamentally flawed! If a user submitted a vague query like 'system broke during upgrade', classification confidence was poor at 0.40, but retrieval matched a generic upgrade doc with 0.94 similarity. The blended average passed 0.70, triggering an auto-response with completely irrelevant steps! Blending allows high retrieval similarity to mask severe classification uncertainty."
    > 
    > *(10:45 – 11:30)* "We redesigned the routing engine around Independent Orthogonal Dual Gates. Auto-response is authorized if and only if: First, classification confidence $c \ge 0.75$. Second, semantic retrieval similarity $s_{\text{ret}} \ge 0.65$. Third, urgency is not CRITICAL. And fourth, safety veto regexes did not flag an active outage. If any single condition fails, the ticket is immediately diverted to human engineers, accompanied by an enriched `EscalationPacket` containing the failed gate reason, inferred intent, and top-2 candidate documentation links. On screen, each gate is shown as its own check, so you can see exactly which one stopped a ticket."
    > 
    > *(11:30 – 12:05)* "When auto-response is authorized, our generation engine in `src/generation/cascade.py` synthesizes the response using strict XML delimiter sandboxing. The prompt encapsulates untrusted user input within `<user_ticket>` tags and retrieved documentation within `<retrieved_context>` tags. System instructions explicitly inform the model that XML content is passive data, neutralizing prompt injection attacks. Furthermore, every claim must cite official document anchors like `[DEPLOY-003]`."
    > 
    > *(12:05 – 12:30)* "To guarantee zero downtime, generation operates through a three-tier cascade: Primary Groq LLM with sub-second execution &rarr; Secondary Gemini 1.5 Flash fallback &rarr; Tertiary Safe Offline Escalation Engine. If cloud APIs are unreachable, our offline engine never outputs speculative guesses—it immediately routes to human engineers with full context. Now, let's transition to the live software demonstration!"

---

## Act VI: LIVE PRODUCT DEMONSTRATION (12:30 – 16:00 / 210s)

*   **Timeline:** `data-start="750"` &bull; `data-duration="210"`
*   **Visual Setup:** Unedited screen recording (first configuration, floor 0.65) of the live dashboard (`assets/in_app_demo.mp4`, produced by `scripts/record_in_app_demo.js`) inside a browser frame, with a sidebar that highlights the scenario on screen. Sidebar timings come from `assets/in_app_demo.marks.json`.
*   **Voiceover Narration (say what the screen shows; the model's exact scores vary a little run to run):**
    > *(12:35 – 13:02) [Overview, then scenario 1]* "This is the running system, not a mock-up. I click scenario one, an API export question. The pipeline normalises the ticket, classifies the intent with confidence 0.90, retrieves the export article with similarity 0.66, and both gates pass. The answer is grounded and cites `[DOC-API-002]` after each step."
    > 
    > *(13:02 – 13:27) [Scenario 2: safety veto]* "Scenario two is a production database outage. Classification confidence is high, but urgency is critical, so the safety veto fires. The router escalates and builds an enriched packet for Tier 2 with the failed gates and the top candidate articles. Notice the packet lists the failed gates and the two best candidate articles, so Tier 2 starts with context."
    > 
    > *(13:27 – 14:18) [Scenarios 3 and 4: router escalations]* "Scenarios three and four are the two gates failing. In both, retrieval similarity (0.33 and 0.14) is below the 0.65 floor, so the ticket escalates with an explicit reason string. The gates are independent: scenario three passes the confidence gate at 0.75 and still fails on similarity. I will come back to this gate in the results, because it is the one that limited our FCR. Watch the reason string on screen. It names the exact gate and the exact numbers, which is what a support manager needs to trust the decision. Nothing here is hidden inside a model. Both tickets are real examples, and the router refused them for different reasons, which is exactly why the two gates are kept separate."
    > 
    > *(14:18 – 14:44) [Scenario 5: guardrail veto]* "Scenario five clears both gates, so a draft is generated, but the grounding check finds a sentence the retrieved text does not support and suppresses the whole answer. This is the guardrail doing its job, and it fired on thirteen of the nineteen generated answers in the validation run. The draft is thrown away entirely, not edited, so a customer never receives a half-supported answer."
    > 
    > *(14:44 – 15:10) [Scenario 6: PII ticket]* "Scenario six contains a card number and an API key. Both are redacted on ingest, before any model sees them. This ticket then escalates at the similarity gate. Redaction and routing are separate controls. The caption on screen shows the text exactly as it is stored: the card and the key are both replaced by markers, two items in all, and that count is kept in the audit record."
    > 
    > *(15:10 – 15:25) [Tamper test]* "Now the tamper test. The dashboard attempts an UPDATE against the decision log. The SQLite trigger `decision_log_no_update` aborts it, so the audit trail is append-only at the database level. The database itself refuses the change."
    > 
    > *(15:25 – 16:00) [Audit log]* "Scrolling down, every decision from this session is in the audit table with intent, confidence, similarity, disposition and routing reason. The unattended run over the full validation set, shown next in the results, writes to the same table. This is the same table that the unattended evaluation reads from. Every decision from this session is there, which is what lets a compliance reviewer reconstruct any answer after the fact. Each row carries the intent, the confidence, the similarity and the routing reason, so an auditor can replay why a ticket was answered or escalated, without asking anyone."

---

## Act VII: Empirical Benchmark Results, Calibration & Retrospective (16:00 – 18:00 / 120s)

*   **Timeline:** `data-start="960"` &bull; `data-duration="120"`
*   **Visual Setup:** Benchmark summary dashboard. Three metric cards (FCR 23.8% not met, ECE 0.093 met, P95 8,220 ms not met) and takeaways: FCR vs correct-routing, the 500-ticket development benchmark, and the label ceiling.
*   **Voiceover Narration:**
    > *(16:00 – 16:34)* "Here is what the measured results say, on the 80-ticket validation set. My first honest run gave first-contact resolution of **7.5 per cent**, against a target of 65. I then made four changes: lowered the retrieval-similarity floor from 0.65 to 0.40, forced sensitive intents such as data residency and security to a human, tightened the generation prompt so answers only restate the sources, and made the guardrail's word matching stem-aware. The final configuration reached **23.8 per cent**: 19 of 80 answered. The target is still missed by a wide margin, and I want to be clear about that."
    >
    > *(16:34 – 17:08)* "What held up: calibration. Expected calibration error is **0.093**, inside our 0.15 target, with intent accuracy at 85 per cent and retrieval precision at three of 92.5 per cent. No must-not-automate ticket was answered, nothing crashed, and all eighty decisions are in the audit log. What did not hold up: five of the nineteen answers we sent were for tickets that should have gone to a person, and P95 latency was 8.2 seconds against a 3-second budget. Rerunning on three low-cost providers with no rate-limit fallbacks gave 20.0 per cent, 16 of 80, so rate limits were not the main constraint."
    >
    > *(17:08 – 17:44)* "I also ran all 500 development tickets through the real pipeline, for about 13 cents; these are in-sample for the parts I tuned. With a larger model, first-contact resolution was **44.2 per cent**, 221 of 500, with one of 87 must-not tickets answered. The correct-routing rate, tickets sent down the right path, is 60.4 per cent for the larger model and 54.4 for the economy mix. It is not first-contact resolution. Only 60 to 62 per cent of tickets are labelled automatable, so 65 per cent would mean answering tickets the labels say need a person."
    >
    > *(17:44 – 18:00)* "Two caveats. The similarity floor was chosen after I saw validation results, so these figures are optimistic, and the hidden set has not been run. Next I would fit thresholds on the development tickets, add provider capacity, and add human review for answer types still wrong-routed. Thank you."

---

## Directorial Production Notes for Clipchamp Splicing

1. **Talking-Head Webcam Intro (0:00 – 2:00)**: Place recorded webcam clip at the start of the Clipchamp timeline. Introduce yourself (Amlan Acharya) and introduce the crisis.
2. **HyperFrames Master Video Composition (2:00 – 18:00)**: Place the rendered 1080p MP4 export from `hyperframes_film/` as the centerpiece.
3. **Talking-Head Webcam Outro (18:00 – 20:00)**: Splice recorded closing reflections at the end.

