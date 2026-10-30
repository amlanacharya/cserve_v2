from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


class CanonicalTicket(BaseModel):
    ticket_id: str
    channel: Literal["email", "chat", "docs_comment", "forum"]
    subject: str | None = None
    body: str
    sender_ref: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    heading_path: str
    text: str
    ordinal: int
    similarity: float | None = None


class EscalationPacket(BaseModel):
    ticket_id: str
    final_disposition: Literal["ESCALATED_ROUTER", "ESCALATED_GUARDRAIL", "ESCALATED_ERROR"]
    routing_reason: str
    inferred_intent: str
    intent_confidence: float
    intent_alternatives: dict[str, float] = Field(default_factory=dict)
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    candidate_docs: list[DocumentChunk] = Field(default_factory=list)
    guardrail_violations: list[str] = Field(default_factory=list)
    provider_used: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProcessedTicketResult(BaseModel):
    ticket_id: str
    channel: str
    final_disposition: Literal["AUTO_RESOLVED", "ESCALATED_ROUTER", "ESCALATED_GUARDRAIL", "ESCALATED_ERROR"]
    final_response: str | None = None
    citations: list[str] = Field(default_factory=list)
    escalation_packet: EscalationPacket | None = None
    inferred_intent: str
    intent_confidence: float
    urgency: str
    top_retrieval_score: float = 0.0
    routing_reason: str
    provider_used: str
    is_degraded: bool = False
    latency_ms: float = 0.0

