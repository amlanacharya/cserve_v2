# Video Presentation Runbook & Production Guide

**Student Name:** Amlan Acharya  
**Project:** CloudServe Support Orchestrator Capstone  
**Target Duration:** 18–20 Minutes  
**Final Output File:** `01_Video/AmlanAcharya_Capstone_Presentation.mp4`  

---

## 1. Structure & Clipchamp Splicing Plan

The video presentation is structured into three continuous segments:

| Segment | Video Timestamp | Visual Content | Audio / Speaker | Production Notes |
|---|---|---|---|---|
| **Part 1: Executive Introduction** | 0:00 – 2:00 | Talking-head webcam video (Amlan Acharya) | Executive hook, baseline crisis (FCR 42%), core thesis | Recorded via webcam; placed as the opening clip in Clipchamp |
| **Part 2: HyperFrames Slides & Live Demo** | 2:00 – 18:00 | Screen recording of `presentation/index.html` + Terminal Live Demo | Deep-dive slide walkthrough and live terminal demo ($\ge 7$ min) | Screen-recorded at 1080p 60fps; main timeline clip |
| **Part 3: Reflection & Conclusion** | 18:00 – 20:00 | Talking-head webcam video (Amlan Acharya) | Architectural retrospective, key learnings, closing | Recorded via webcam; placed as the closing clip in Clipchamp |

---

## 2. Recording Instructions

### 2.1 Presenter Deck (`presentation/index.html`)
1. Open `presentation/index.html` in Chrome, Edge, or Firefox.
2. Press `F11` to enter full-screen mode.
3. Use `Right Arrow` / `Space` to advance slides and `Left Arrow` to navigate backward.
4. Press `N` to toggle the presenter notes bar if needed.

### 2.2 Live Software Demonstration (Minutes 8:00 – 15:30)
Run the commands sequentially in PowerShell or Windows Terminal:

```powershell
# 1. Clean test suite run verifying all 35 tests
.\.venv\Scripts\pytest tests/ -v

# 2. Start the FastAPI orchestrator in the background or split pane
.\.venv\Scripts\uvicorn src.api:app --host 120.0.0.1 --port 8000

# 3. Process an auto-respond ticket (API key rotation query)
curl.exe -X POST http://127.0.0.1:8000/tickets/process `
  -H "Content-Type: application/json" `
  -d '{\"id\": \"DEMO-001\", \"channel\": \"chat\", \"customer_id\": \"cust_77\", \"subject\": \"How do I rotate API key?\", \"body\": \"I need to rotate my production API key without downtime.\", \"metadata\": {}}'

# 4. Process an outage ticket triggering safety veto and escalation
curl.exe -X POST http://127.0.0.1:8000/tickets/process `
  -H "Content-Type: application/json" `
  -d '{\"id\": \"DEMO-002\", \"channel\": \"email\", \"customer_id\": \"cust_99\", \"subject\": \"Production down database corrupt\", \"body\": \"Our entire database is corrupted and the service is completely down!\", \"metadata\": {}}'

# 5. Inspect the immutable SQLite decision log
python -c "import sqlite3; conn = sqlite3.connect('data/decision_log.db'); print(conn.execute('SELECT ticket_id, final_status, routing_reason FROM decision_log ORDER BY rowid DESC LIMIT 2').fetchall())"

# 6. Execute batch evaluation harness with progress bar
.\.venv\Scripts\python -m evaluation.harness --input 05_Datasets/development_tickets.json --output evaluation/results/evaluation_report.json --delay 1.5
```

---

## 3. Microsoft Clipchamp Assembly Workflow

1. Open **Microsoft Clipchamp** (pre-installed in Windows 11 or available via web/app).
2. Click **Create a new video** (16:9 widescreen, 1080p).
3. Import the following media files:
   - `webcam_intro.mp4` (Recorded talking-head webcam video, 0:00–2:00)
   - `screen_deck_and_demo.mp4` (Screen recording of slides & live terminal demo, 2:00–18:00)
   - `webcam_outro.mp4` (Recorded talking-head webcam video, 18:00–20:00)
4. Drag clips onto the timeline in sequential order:
   `[webcam_intro (2 min)]` &rarr; `[screen_deck_and_demo (16 min)]` &rarr; `[webcam_outro (2 min)]`.
5. Add a subtle 0.5-second cross-fade or clean cut transition between clips.
6. Verify audio levels are consistent across all three clips.
7. Click **Export** &rarr; Select **1080p (HD)**.
8. Save the exported file as `01_Video/AmlanAcharya_Capstone_Presentation.mp4`.

