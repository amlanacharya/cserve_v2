from typing import Any, Literal, TypedDict
from src.core.models import CanonicalTicket, DocumentChunk, EscalationPacket


class AgentState(TypedDict, total=False):
    # Pipeline Identification & Input
    run_id: str
    raw_ticket: dict[str, Any]

    # Ingestion Stage
    canonical_ticket: CanonicalTicket | None

    # Classification Stage
    inferred_intent: str
    intent_alternatives: dict[str, float]
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    confidence: float
    must_not_auto_respond: bool

    # Retrieval Stage
    retrieved_docs: list[DocumentChunk]
    top_retrieval_score: float

    # Routing Stage
    routing_action: Literal["AUTO_RESPOND", "ESCALATE"]
    routing_reason: str

    # Generation Stage
    draft_response: str | None
    citations: list[str]

    # Guardrails Stage
    guardrail_status: Literal["PASSED", "TRIPPED"] | None
    guardrail_violations: list[str]

    # Escalation Stage
    escalation_packet: EscalationPacket | None

    # Audit & Final Disposition
    final_response: str | None
    final_disposition: Literal[
        "AUTO_RESOLVED", "ESCALATED_ROUTER", "ESCALATED_GUARDRAIL", "ESCALATED_ERROR"
    ]
    provider_used: str
    started_at: float  # time.perf_counter() at pipeline entry
    is_degraded: bool
    error_details: str | None
    db_path: str | None

