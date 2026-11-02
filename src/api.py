import sqlite3
from pathlib import Path
from typing import Any
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
