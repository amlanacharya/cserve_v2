# HyperFrames 18-Minute Architectural Film & In-App Demo Runbook

**Production Title:** CloudServe Support Orchestrator — Architectural Film & Live Demo  
**Director & Lead Engineer:** Amlan Acharya  
**Design Palette:** Executive White & Royal Blue Enterprise Theme  
**Framework:** [HeyGen HyperFrames](https://github.com/heygen-com/hyperframes) (`npx hyperframes`)  
**Canvas Resolution:** 1920 &times; 1080 (1080p Full HD) &bull; 30 fps  
**Film Duration:** Exactly 18 Minutes (1,080 Seconds / 32,400 Frames)  
**Total Video with Webcam (Clipchamp):** 20 Minutes (2:00 Intro + 18:00 Core Presentation + 2:00 Outro)  

---

## 1. Video Deliverables Summary

This directory contains two complementary video artifacts designed for immediate review and Clipchamp splicing:

1. **`01_Video/in_app_demo_live.mp4`** (1.06 MB, 1080p Full HD):
   - **Direct Live Screen Recording** of the running FastAPI web application (`http://127.0.0.1:8000/dashboard`).
   - Driven programmatically via Puppeteer and encoded with FFmpeg.
   - Shows interactive multi-channel ticket submission, live animated 7-stage pipeline visualizer, orthogonal dual-gate meters, grounded `[DOC-ID]` citation badges, live SQLite audit stream, and tamper-test trigger rejection (`decision_log_no_update`).

2. **`01_Video/hyperframes_presentation_18min.mp4`** (Master 18:00 Film):
   - **Comprehensive Executive Film** rendered directly via HeyGen HyperFrames.
   - Built with an executive White & Slate ground (`#f8fafc` / `#ffffff`), deep navy typography (`#0f172a`), and royal blue accenting (`#1d4ed8` / `#2563eb`), removing all informal rehearsal kickers.
   - Seamlessly integrates the full architectural thesis, multi-channel ingestion, bounded chunking, dual gates, live in-app control plane simulation, and empirical benchmark evaluation.

---

## 2. Directorial Structure & Pacing Map

The 18-minute core film is structured into 7 distinct sections, adhering to the HeyGen HyperFrames sub-composition contract (`index.html` + `compositions/act*.html`):

| Section | Identifier | Time Offset | Duration | Core Visuals & Demonstration Content |
|---|---|---|---|---|
| **Section 1** | `act1_crisis.html` | 0:00 – 2:30 | 150s | **Problem Discovery & Vocabulary Mismatch:** The 42.0% FCR crisis vs 65.0% mandate; 500-ticket EDA; colloquial query divergence. |
| **Section 2** | `act2_architecture.html` | 2:30 – 5:00 | 150s | **System Design Thesis:** Clean Architecture domain model; why microservices fail; LangGraph StateGraph & `@safe_node` defensive isolation. |
| **Section 3** | `act3_ingestion.html` | 5:00 – 7:30 | 150s | **Ingestion & PII Defense:** Multi-channel normalizer (`email`, `chat`, `forum`, `docs_comment`); Luhn algorithm checksum validation; API key regex redaction. |
| **Section 4** | `act4_retrieval.html` | 7:30 – 10:00 | 150s | **Semantic Retrieval & Chunking:** Bounded H2/H3 chunking (87 chunks across 29 articles); ChromaDB 0.3.21 dense embeddings; Pydantic v2 backward compatibility shim. |
| **Section 5** | `act5_routing.html` | 10:00 – 12:30 | 150s | **Orthogonal Dual Gates & Cascade:** Independent dual gates ($c \ge 0.75, s_{\text{ret}} \ge 0.65$); XML prompt sandboxing; 3-tier cascade (Groq &rarr; Gemini &rarr; Offline Mock). |
| **Section 6** | `act6_demo.html` | 12:30 – 16:00 | 210s | **Live In-App Control Plane:** Full interactive web dashboard inside browser frame demonstrating Scenario 1 (Auto-Response), Scenario 2 (Safety Veto Outage), Scenario 3 (PII/Luhn Redaction), and Scenario 4 (SQLite Immutability Trigger Test). |
| **Section 7** | `act7_results.html` | 16:00 – 18:00 | 120s | **Empirical Benchmarks & Retrospective:** 68.3% FCR (+26.3% uplift), 0.074 10-bin ECE curve, P95 latency (2,150ms), and 12/12 acceptance criteria validation. |

---

## 3. Running the Live Application & HyperFrames Studio

### 3.1 Launching the Live FastAPI Web Dashboard
The web application provides a full graphical control plane with one-click test scenarios and live SQLite inspection:

```powershell
# Start the server (if not already running)
.\.venv\Scripts\uvicorn src.api:app --host 127.0.0.1 --port 8000
```
Open your browser to: **`http://127.0.0.1:8000/dashboard`** (or `http://127.0.0.1:8000/`).

### 3.2 HyperFrames Live Studio Preview
To inspect or interact with the seekable 18-minute presentation timeline:

```bash
cd hyperframes_film
npm run dev
# or: npx hyperframes preview
```

### 3.3 Quality Gate Validation
```bash
cd hyperframes_film
npm run check
```
*(Verified: Passed with 0 errors across all 599 frame crafts, 0 layout shifts, 0 runtime exceptions).*

### 3.4 Re-recording Live In-App Video
To re-run the automated headless browser demo recording:

```bash
node scripts/record_in_app_demo.js
```
This generates `01_Video/in_app_demo_live.mp4` directly using Puppeteer and FFmpeg.

---

## 4. Microsoft Clipchamp Assembly Workflow

To assemble the complete 20-minute capstone submission with your webcam talking-head clips:

1. **Webcam Intro Clip (0:00 – 2:00)**:
   - Record yourself on webcam (Clipchamp or Windows Camera).
   - Script guide: *"Hi, I'm Amlan Acharya, and this is the CloudServe Support Orchestrator Capstone..."*
   - Highlight the 42% baseline FCR crisis, SLA penalties, and executive mandate for 65% FCR.
2. **Main Film & In-App Demo Clip (2:00 – 18:00)**:
   - Import `01_Video/hyperframes_presentation_18min.mp4` (or splice in `01_Video/in_app_demo_live.mp4` for Act 6).
   - Follow the minute-by-minute speaking cues in [hyperframes_film/DIRECTOR_SCRIPT.md](file:///c:/Users/amlan/Downloads/cloudserve/FDE_Capstone_Complete/Capstone_Pack/hyperframes_film/DIRECTOR_SCRIPT.md).
3. **Webcam Outro Clip (18:00 – 20:00)**:
   - Record yourself reflecting on key lessons: why confidence calibration (ECE 0.074) trumps raw accuracy, how orthogonal dual gates eliminate hallucinated answers, and the value of tamper-evident audit logs.
4. **Assembly & Export in Clipchamp**:
   - Open **Microsoft Clipchamp** &rarr; New Project (16:9, 1080p).
   - Arrange: `[Webcam Intro (2m)]` &rarr; `[HyperFrames Film & Demo (18m)]` &rarr; `[Webcam Outro (2m)]`.
   - Add a subtle 0.5s cross-dissolve transition between clips.
   - Click **Export &rarr; 1080p (HD)** and save to `01_Video/AmlanAcharya_Capstone_Presentation.mp4`.

---

## 5. Documentation References

- **Director's Production Specification:** [hyperframes_film/SPEC.md](file:///c:/Users/amlan/Downloads/cloudserve/FDE_Capstone_Complete/Capstone_Pack/hyperframes_film/SPEC.md)
- **18-Minute Second-by-Second Narration Script:** [hyperframes_film/DIRECTOR_SCRIPT.md](file:///c:/Users/amlan/Downloads/cloudserve/FDE_Capstone_Complete/Capstone_Pack/hyperframes_film/DIRECTOR_SCRIPT.md)
- **Master Composition:** [hyperframes_film/index.html](file:///c:/Users/amlan/Downloads/cloudserve/FDE_Capstone_Complete/Capstone_Pack/hyperframes_film/index.html)
- **Sub-Compositions:** [hyperframes_film/compositions/](file:///c:/Users/amlan/Downloads/cloudserve/FDE_Capstone_Complete/Capstone_Pack/hyperframes_film/compositions/)
