from datetime import datetime, timezone
from typing import Literal
from src.core.config import get_settings
from src.core.models import DocumentChunk, EscalationPacket


def build_escalation_packet(
    ticket_id: str,
    final_disposition: Literal["ESCALATED_ROUTER", "ESCALATED_GUARDRAIL", "ESCALATED_ERROR"],
    routing_reason: str,
    inferred_intent: str,
    intent_confidence: float,
    intent_alternatives: dict[str, float] | None,
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"],
    candidate_docs: list[DocumentChunk],
    provider_used: str,
    guardrail_violations: list[str] | None = None,
) -> EscalationPacket:
    """
    Builds an enriched, structured EscalationPacket attaching top candidate documents
    from the retrieval cache and audit context.
    """
    settings = get_settings()
    top_k_escalate = settings.top_k_escalate

    # Attach top candidate chunks (up to k_escalate)
    candidates = candidate_docs[:top_k_escalate] if candidate_docs else []

    return EscalationPacket(
        ticket_id=ticket_id,
        final_disposition=final_disposition,
        routing_reason=routing_reason,
        inferred_intent=inferred_intent,
        intent_confidence=intent_confidence,
        intent_alternatives=intent_alternatives or {},
        urgency=urgency,
        candidate_docs=candidates,
        guardrail_violations=guardrail_violations or [],
        provider_used=provider_used,
        created_at=datetime.now(timezone.utc),
    )

