import time
import uuid
from typing import Any
from langgraph.graph import END, StateGraph
from src.core.models import ProcessedTicketResult
from src.orchestrator.nodes import (
    audit_node,
    classify_node,
    escalate_node,
    generation_node,
    guardrails_node,
    normalize_node,
    retrieval_node,
    routing_node,
)
from src.orchestrator.state import AgentState


def route_decision(state: dict[str, Any]) -> str:
    if state.get("routing_action") == "AUTO_RESPOND":
        return "generate"
    return "escalate"


def generate_decision(state: dict[str, Any]) -> str:
    draft = state.get("draft_response")
    if draft and str(draft).strip():
        return "guardrails"
    return "escalate"


def guardrails_decision(state: dict[str, Any]) -> str:
    if state.get("guardrail_status") == "PASSED":
        return "audit"
    return "escalate"


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("normalize", normalize_node)
    builder.add_node("classify", classify_node)
    builder.add_node("retrieve", retrieval_node)
    builder.add_node("route", routing_node)
    builder.add_node("generate", generation_node)
    builder.add_node("guardrails", guardrails_node)
    builder.add_node("escalate", escalate_node)
    builder.add_node("audit", audit_node)

    builder.set_entry_point("normalize")

    builder.add_edge("normalize", "classify")
    builder.add_edge("classify", "retrieve")
    builder.add_edge("retrieve", "route")

    builder.add_conditional_edges(
        "route",
        route_decision,
        {"generate": "generate", "escalate": "escalate"},
    )

    builder.add_conditional_edges(
        "generate",
        generate_decision,
        {"guardrails": "guardrails", "escalate": "escalate"},
    )

    builder.add_conditional_edges(
        "guardrails",
        guardrails_decision,
        {"audit": "audit", "escalate": "escalate"},
    )

    builder.add_edge("escalate", "audit")
    builder.add_edge("audit", END)

    return builder.compile()


class SupportOrchestrator:
    def __init__(self):
        self.workflow = build_graph()

    def process_ticket(
        self,
        raw_ticket: dict[str, Any],
        run_id: str | None = None,
    ) -> ProcessedTicketResult:
        start_time = time.perf_counter()
        run_id_val = run_id or f"run_{uuid.uuid4().hex[:8]}"

        initial_state: dict[str, Any] = {
            "run_id": run_id_val,
            "raw_ticket": raw_ticket,
            "is_degraded": False,
            "error_details": None,
            "guardrail_violations": [],
            "citations": [],
            "execution_latency_ms": 0.0,
        }

        final_state = self.workflow.invoke(initial_state)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        canonical = final_state.get("canonical_ticket")
        ticket_id = (
            canonical.ticket_id
            if canonical
            else str(raw_ticket.get("ticket_id", "UNKNOWN"))
        )
        channel = (
            canonical.channel
            if canonical
            else str(raw_ticket.get("channel", "email"))
        )

        return ProcessedTicketResult(
            ticket_id=ticket_id,
            channel=channel,
            final_disposition=final_state.get("final_disposition", "ESCALATED_ERROR"),
            final_response=final_state.get("final_response"),
            citations=final_state.get("citations", []),
            escalation_packet=final_state.get("escalation_packet"),
            inferred_intent=final_state.get("inferred_intent", "unknown"),
            intent_confidence=float(final_state.get("confidence", 0.0)),
            urgency=str(final_state.get("urgency", "MEDIUM")),
            top_retrieval_score=float(final_state.get("top_retrieval_score", 0.0)),
            routing_reason=str(final_state.get("routing_reason", "")),
            provider_used=str(final_state.get("provider_used", "offline_mock")),
            is_degraded=bool(final_state.get("is_degraded", False)),
            latency_ms=elapsed_ms,
        )

