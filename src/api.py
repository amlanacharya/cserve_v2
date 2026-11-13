import sqlite3
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from src.core.config import get_settings
from src.core.models import ProcessedTicketResult
from src.orchestrator import SupportOrchestrator

app = FastAPI(
    title="CloudServe Support Orchestrator API",
    version="0.1.0",
    description="Automated First-Contact Resolution and Enriched Escalation REST Service",
)

orchestrator = SupportOrchestrator()
_TEMPLATE_PATH = Path(__file__).parent / "templates" / "dashboard.html"


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard() -> HTMLResponse:
    """Serves the interactive in-app Support Orchestrator dashboard."""
    if _TEMPLATE_PATH.exists():
        return HTMLResponse(content=_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>CloudServe Support Orchestrator API</h1><p>Dashboard template not found.</p>")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint confirming service status."""
    return {"status": "ok"}


@app.post("/tickets/process", response_model=ProcessedTicketResult)
def process_ticket_endpoint(raw_ticket: dict[str, Any]) -> ProcessedTicketResult:
    """
    Ingests and processes a customer support ticket across email, chat, docs_comment, or forum.
    Returns the ProcessedTicketResult outcome.
    """
    if not isinstance(raw_ticket, dict) or not raw_ticket:
        raise HTTPException(status_code=400, detail="Invalid ticket payload: expected non-empty JSON object")

    try:
        result = orchestrator.process_ticket(raw_ticket)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal processing failure: {str(e)}")


@app.get("/api/decisions/recent")
def get_recent_decisions(limit: int = 20) -> list[dict[str, Any]]:
    """Returns recent decision log entries from the immutable SQLite WAL store."""
    settings = get_settings()
    db_path = Path(settings.decision_log_path)
    if not db_path.exists():
        return []

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, ticket_id, channel, inferred_intent, urgency, intent_confidence, "
            "top_retrieval_score, final_disposition, routing_reason, logged_at "
            "FROM decision_log ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        return []


@app.post("/api/test/tamper")
def test_database_tamper() -> dict[str, str]:
    """Attempts an illegal UPDATE statement to demonstrate SQLite trigger immutability."""
    settings = get_settings()
    db_path = Path(settings.decision_log_path)
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not initialized yet")

    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE decision_log SET final_disposition = 'TAMPERED' WHERE id = 1")
        conn.commit()
        conn.close()
        return {"status": "unprotected", "message": "WARNING: UPDATE unexpectedly succeeded"}
    except Exception as e:
        return {
            "status": "immutable_protected",
            "message": f"SQLite Trigger Aborted Mutation: {str(e)}"
        }


class AgentFeedback(BaseModel):
    agent_id: str
    agent_tier: Literal["TIER_1", "TIER_2", "TECH_WRITER"]
    agent_action: Literal["ACCEPTED_AS_IS", "EDITED_AND_SENT", "REJECTED_ESCALATED", "RESOLVED_BY_TIER2"]
    actual_true_intent: str | None = None
    flag_for_tech_writer: bool = False
    failure_attribution: Literal["DOC_MISSING", "DOC_OUTDATED", "AI_MISINTERPRETED", "NONE"] = "NONE"
    agent_notes: str | None = None
    customer_csat_score: int | None = None


_FEEDBACK_DDL = """CREATE TABLE IF NOT EXISTS agent_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT NOT NULL, agent_id TEXT NOT NULL,
    agent_tier TEXT NOT NULL, agent_action TEXT NOT NULL, actual_true_intent TEXT,
    flag_for_tech_writer INTEGER NOT NULL, failure_attribution TEXT NOT NULL, agent_notes TEXT,
    customer_csat_score INTEGER CHECK (customer_csat_score IS NULL OR customer_csat_score BETWEEN 1 AND 5),
    created_at TEXT NOT NULL)"""


@app.post("/tickets/{ticket_id}/feedback")
def submit_feedback(ticket_id: str, fb: AgentFeedback) -> dict[str, str]:
    """Records a human agent's verdict on a decision. Separate table: decision_log stays append-only and unchanged."""
    if fb.customer_csat_score is not None and not 1 <= fb.customer_csat_score <= 5:
        raise HTTPException(status_code=422, detail="customer_csat_score must be 1..5")
    db_path = Path(get_settings().decision_log_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=5.0)
    try:
        conn.execute(_FEEDBACK_DDL)
        conn.execute(
            "INSERT INTO agent_feedback (ticket_id, agent_id, agent_tier, agent_action, actual_true_intent, "
            "flag_for_tech_writer, failure_attribution, agent_notes, customer_csat_score, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (ticket_id, fb.agent_id, fb.agent_tier, fb.agent_action, fb.actual_true_intent,
             int(fb.flag_for_tech_writer), fb.failure_attribution, fb.agent_notes,
             fb.customer_csat_score, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    return {"status": "recorded", "ticket_id": ticket_id}
