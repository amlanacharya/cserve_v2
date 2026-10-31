from typing import Any, Mapping, TypedDict
from pydantic import BaseModel, Field
from src.core.models import CanonicalTicket, DocumentChunk, EscalationPacket, ProcessedTicketResult
from src.core.types import (
    DEFAULT_URGENCY,
    OFFLINE_PROVIDER,
    Disposition,
    EscalatedDisposition,
    GuardrailStatus,
    Provider,
    RoutingAction,
    Urgency,
)
from src.routing.escalation import build_escalation_packet


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
    failed_node: str | None  # set by a node's crash fallback; routing reports NODE_FAILURE
    db_path: str | None


def initial_state(
    run_id: str, raw_ticket: dict[str, Any], started_at: float, db_path: str | None
) -> AgentState:
    """Seed values for a pipeline run; everything else defaults in RunSnapshot."""
    return {
        "run_id": run_id,
        "raw_ticket": raw_ticket,
        "is_degraded": False,
        "error_details": None,
        "guardrail_violations": [],
        "citations": [],
        "started_at": started_at,
        "db_path": db_path,
    }


class RunSnapshot(BaseModel):
    """Typed, defaulted read-view of the graph state. Single home for state defaults.

    Build with RunSnapshot.from_state(state); nodes read fields instead of
    state.get(key, default), and the escalation call, audit record and final
    result are all derived from it.
    """

    run_id: str = "default_run"
    canonical_ticket: CanonicalTicket | None = None
    inferred_intent: str = "unknown"
    intent_alternatives: dict[str, float] = Field(default_factory=dict)
    urgency: Urgency = DEFAULT_URGENCY
    confidence: float = 0.0
    must_not_auto_respond: bool = False
    retrieved_docs: list[DocumentChunk] = Field(default_factory=list)
    top_retrieval_score: float = 0.0
    routing_action: RoutingAction = "ESCALATE"
    routing_reason: str = ""
    draft_response: str | None = None
    citations: list[str] = Field(default_factory=list)
    guardrail_status: GuardrailStatus | None = None
    guardrail_violations: list[str] = Field(default_factory=list)
    escalation_packet: EscalationPacket | None = None
    final_response: str | None = None
    final_disposition: Disposition = "ESCALATED_ERROR"
    provider_used: Provider = OFFLINE_PROVIDER
    started_at: float | None = None
    is_degraded: bool = False
    error_details: str | None = None
    db_path: str | None = None

    @classmethod
    def from_state(cls, state: Mapping[str, Any]) -> "RunSnapshot":
        return cls.model_validate({k: v for k, v in state.items() if k in cls.model_fields})

    def was_set(self, field: str) -> bool:
        return field in self.model_fields_set

    def to_escalation_packet(self, disposition: EscalatedDisposition) -> EscalationPacket:
        assert self.canonical_ticket is not None
        return build_escalation_packet(
            ticket_id=self.canonical_ticket.ticket_id,
            final_disposition=disposition,
            routing_reason=self.routing_reason if self.was_set("routing_reason") else "Escalated",
            inferred_intent=self.inferred_intent,
            intent_confidence=self.confidence,
            intent_alternatives=self.intent_alternatives,
            urgency=self.urgency,
            candidate_docs=self.retrieved_docs,
            provider_used=self.provider_used,
            guardrail_violations=self.guardrail_violations,
        )

    def to_audit_record(self, latency_ms: float) -> dict[str, Any]:
        assert self.canonical_ticket is not None
        return {
            "run_id": self.run_id,
            "ticket_id": self.canonical_ticket.ticket_id,
            "channel": self.canonical_ticket.channel,
            "inferred_intent": self.inferred_intent,
            "intent_confidence": self.confidence,
            "intent_alternatives": self.intent_alternatives,
            "urgency": self.urgency,
            "top_retrieval_score": self.top_retrieval_score,
            "must_not_auto_respond": self.must_not_auto_respond,
            "routing_action": self.routing_action,
            "routing_reason": self.routing_reason,
            "guardrail_status": self.guardrail_status,
            "final_disposition": self.final_disposition,
            "citations": self.citations,
            "provider_used": self.provider_used,
            "is_degraded": self.is_degraded,
            "error_details": self.error_details,
            "guardrail_violations": self.guardrail_violations,
            "latency_ms": latency_ms,
        }

    def to_result(self, raw_ticket: Mapping[str, Any], latency_ms: float) -> ProcessedTicketResult:
        ticket = self.canonical_ticket
        return ProcessedTicketResult(
            ticket_id=ticket.ticket_id if ticket else str(raw_ticket.get("ticket_id", "UNKNOWN")),
            channel=ticket.channel if ticket else str(raw_ticket.get("channel", "email")),
            final_disposition=self.final_disposition,
            final_response=self.final_response,
            citations=self.citations,
            escalation_packet=self.escalation_packet,
            inferred_intent=self.inferred_intent,
            intent_confidence=float(self.confidence),
            urgency=self.urgency,
            top_retrieval_score=float(self.top_retrieval_score),
            routing_reason=self.routing_reason,
            provider_used=self.provider_used,
            is_degraded=self.is_degraded,
            latency_ms=latency_ms,
        )

