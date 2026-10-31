from typing import Any, TypedDict
from src.core.models import CanonicalTicket, DocumentChunk, EscalationPacket
from src.core.types import Disposition, GuardrailStatus, Provider, RoutingAction, Urgency


class AgentState(TypedDict, total=False):
    # Pipeline Identification & Input
    run_id: str
    raw_ticket: dict[str, Any]

    # Ingestion Stage
    canonical_ticket: CanonicalTicket | None

    # Classification Stage
    inferred_intent: str
    intent_alternatives: dict[str, float]
    urgency: Urgency
    confidence: float
    must_not_auto_respond: bool

    # Retrieval Stage
    retrieved_docs: list[DocumentChunk]
    top_retrieval_score: float

    # Routing Stage
    routing_action: RoutingAction
    routing_reason: str

    # Generation Stage
    draft_response: str | None
    citations: list[str]

    # Guardrails Stage
    guardrail_status: GuardrailStatus | None
    guardrail_violations: list[str]

    # Escalation Stage
    escalation_packet: EscalationPacket | None

    # Audit & Final Disposition
    final_response: str | None
    final_disposition: Disposition
    provider_used: Provider
    started_at: float  # time.perf_counter() at pipeline entry
    is_degraded: bool
    error_details: str | None
    db_path: str | None

