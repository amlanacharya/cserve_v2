from typing import Any
from fastapi import FastAPI, HTTPException
from src.core.models import ProcessedTicketResult
from src.orchestrator import SupportOrchestrator

app = FastAPI(
    title="CloudServe Support Orchestrator API",
    version="0.1.0",
    description="Automated First-Contact Resolution and Enriched Escalation REST Service",
)

orchestrator = SupportOrchestrator()


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

