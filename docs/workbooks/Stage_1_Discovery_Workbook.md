# Stage 1: Discovery Workbook
## Qualitative & Quantitative Evidence Analysis

**Student Name:** Amlan Acharya  
**Project:** CloudServe Support Orchestrator  
**Phase:** Week One &bull; Days One to Three  
**Status:** Completed &amp; Verified  

---

### Section 1: Stakeholder Interview Evidence Matrix

| Stakeholder | What They Told Us | What They Appear Not to Know | Data Verification Target |
|---|---|---|---|
| **Marcus Adeyemi**<br>*(Head of Support)* | Support operations are experiencing severe margin compression. First-Contact Resolution (FCR) is at **42%** against an executive mandate of **65%**. Believes Tier 1 agents are too slow and that unconstrained generative AI can deflect 75% of inquiries immediately. | Unaware that 70% of tickets are repeat inquiries with existing answers in the 29 KB articles, and that vocabulary mismatch—not agent speed—is preventing findability. | Measure baseline FCR, repetitive inquiry clustering, and document coverage in `05_Datasets/development_tickets.json`. |
| **Sofia Restrepo**<br>*(Tier 1 Support Agent)* | Agents spend over 65% of their handle time searching fragmented documentation wikis. Technical articles are written in dense, internal engineering terminology that fails to match colloquial customer phrasing. Under strict 10-minute queue SLA limits, agents are forced to escalate. | Unaware of the downstream engineering bottleneck caused by escalating tickets without diagnostic context (the "escalation black hole"). | Measure average handle time and search failure rate on colloquial customer queries. |
| **Daniel Okonkwo**<br>*(Tier 2 Infrastructure Lead)* | Senior infrastructure engineers spend 40% of their sprint capacity resolving routine deployment and authentication tickets. Complained that escalations lack structured diagnostic context, forcing senior engineers to repeat basic discovery questions. | Unaware of the high cognitive load, lack of semantic search tools, and rigid queue SLA clocks imposed on front-line Tier 1 agents. | Measure the proportion of escalated tickets that had verifiable solutions in existing documentation (the 50% preventable rate). |
| **Ines Varga**<br>*(Technical Documentation Writer)* | Confirmed all 29 knowledge base articles are technically accurate, reviewed, and sufficient for common customer operational issues. Believes documentation is discoverable because all product features are covered. | Does not recognize that customers and non-fluent English speakers use colloquial symptoms (*"build keeps dying"*) rather than formal technical titles (*"resolving container health check failures"*). | Compare unigram and semantic overlap between ticket bodies and article titles across the 29 articles. |
| **Ravi Menon**<br>*(Enterprise Customer)* | Expressed severe frustration that production-downtime inquiries wait in generic queues, while simple API key and password questions take hours to answer. Experiences degraded trust when automated bots provide vague or incorrect answers. | Unaware of internal queuing and manual routing mechanisms. | Analyze CSAT correlation with resolution latency and channel origin. |

---

### Section 2: Settling Disagreements with Data

| The Disagreement | Who Says What | Empirical Data Settlement | Architectural Consequence |
|---|---|---|---|
| **Is documentation complete or missing?** | Ines asserts documentation covers all issues; Sofia claims critical resolution steps are missing. | Exploratory analysis across 500 tickets shows documentation covers **73.2%** of issues, but keyword search fails on lexical vocabulary mismatch. | Dense semantic retrieval using ChromaDB and `all-MiniLM-L6-v2` embeddings is mandatory; rewriting documentation is not. |
| **Are Tier 1 agents escalating prematurely?** | Daniel claims 50% of escalations are unnecessary; Sofia states escalations are forced by 10-minute SLA limits. | Data confirms **51.4%** of escalated tickets had exact answers in existing documentation articles. | The system must automatically attach the top-2 candidate documentation links to all escalated tickets. |
| **Is automated auto-response safe for customer trust?** | Marcus wants aggressive deflection; the Security Officer and Daniel demand zero-tolerance on errors. | Data shows customer satisfaction drops sharply (CSAT=1) on incorrect responses or ungrounded claims. | Implement independent dual-gate routing ($\tau=0.75, \sigma=0.65$), XML delimiter sandboxing, and active guardrails. |

---

### Section 3: Exploratory Data Analysis (500 Production Development Tickets)

*   **Total Tickets Analyzed:** 500
*   **Channel Distribution:**
    *   Chat: 175 tickets (35.0%)
    *   Email: 150 tickets (30.0%)
    *   Forum: 100 tickets (20.0%)
    *   Documentation Comments: 75 tickets (15.0%)
*   **Intent Taxonomy:**
    *   `deployment_failure`: 142 tickets (28.4%)
    *   `authentication_failure`: 126 tickets (25.2%)
    *   `billing_query`: 108 tickets (21.6%)
    *   `rate_limiting`: 74 tickets (14.8%)
    *   `general_inquiry` / Ambiguous: 50 tickets (10.0%)
*   **Urgency Distribution:**
    *   `MEDIUM`: 310 tickets (62.0%)
    *   `HIGH`: 120 tickets (24.0%)
    *   `LOW`: 50 tickets (10.0%)
    *   `CRITICAL`: 20 tickets (4.0%)
*   **Baseline First-Contact Resolution (FCR):** 42.0% (210 / 500)
*   **Average CSAT Rating:** 2.85 / 5.0
*   **Proportion Answerable from Documentation:** 73.2% (366 / 500)

---

### Section 4: The Synthesized Problem Statement

> **Problem Statement:**  
> CloudServe customer support operations suffer from an artificially depressed First-Contact Resolution rate of 42% (target 65%) and an average resolution time of 18.4 hours, driven not by lack of documentation but by vocabulary mismatch that blinds keyword search, and an unstructured escalation pipeline that forces senior engineers to repeat basic discovery on routine tickets. The solution requires a decoupled modular monolith combining multi-channel ingestion, dense semantic retrieval over 29 curated articles, independent dual-gate routing (confidence $\ge 0.75$, similarity $\ge 0.65$), citation-grounded answer generation, active guardrail blocking, and enriched escalation packaging.

