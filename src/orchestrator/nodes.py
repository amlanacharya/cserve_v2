import sys
from typing import Any
from src.audit.logger import log_decision
from src.classify.classifier import classify_ticket
from src.core.config import get_settings
from src.generation.generator import generate_response
from src.guardrails import evaluate_guardrails
from src.ingest.normalizer import normalize_ticket_with_stats
from src.orchestrator.state import RunSnapshot, elapsed_ms
from src.orchestrator.wrappers import safe_node
from src.retrieval.store import query_documents
from src.routing.router import evaluate_route


@safe_node(node_name="normalize_node")
def normalize_node(state: dict[str, Any]) -> dict[str, Any]:
    raw_payload = state.get("raw_ticket", {})
    canonical, redactions = normalize_ticket_with_stats(raw_payload)
    return {"canonical_ticket": canonical, "pii_redactions_count": redactions}


@safe_node(node_name="classify_node")
def classify_node(state: dict[str, Any]) -> dict[str, Any]:
    ticket = state["canonical_ticket"]
    cls_res = classify_ticket(ticket)
    return {
        "inferred_intent": cls_res["inferred_intent"],
        "intent_alternatives": cls_res["intent_alternatives"],
        "urgency": cls_res["urgency"],
        "confidence": cls_res["confidence"],
        "must_not_auto_respond": cls_res["must_not_auto_respond"],
        "provider_used": cls_res["provider_used"],
        "classification_provider": cls_res["provider_used"],
    }


@safe_node(node_name="retrieval_node")
def retrieval_node(state: dict[str, Any]) -> dict[str, Any]:
    ticket = state["canonical_ticket"]
    settings = get_settings()
    query_text = f"{ticket.subject or ''} {ticket.body}".strip()

    chunks = query_documents(query_text=query_text, top_k=settings.top_k_passages)
    top_score = chunks[0].similarity if chunks and chunks[0].similarity is not None else 0.0
    return {
        "retrieved_docs": chunks,
        "top_retrieval_score": top_score,
        "retrieval_k": settings.top_k_passages,
    }


@safe_node(node_name="routing_node")
def routing_node(state: dict[str, Any]) -> dict[str, Any]:
    action, reason = evaluate_route(
        confidence=state["confidence"],
        top_retrieval_score=state["top_retrieval_score"],
        urgency=state["urgency"],
        must_not_auto_respond=state["must_not_auto_respond"],
        provider_used=state.get("provider_used"),
        node_failure=state.get("failed_node"),
    )
    return {
        "routing_action": action,
        "routing_reason": reason,
    }


@safe_node(node_name="generation_node")
def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    ticket = state["canonical_ticket"]
    gen_res = generate_response(
        subject=ticket.subject,
        body=ticket.body,
        retrieved_docs=state.get("retrieved_docs", []),
    )
    updates: dict[str, Any] = {
        "draft_response": gen_res["draft_response"],
        "citations": gen_res["citations"],
    }
    if gen_res.get("provider_used"):
        updates["provider_used"] = gen_res["provider_used"]
    return updates


@safe_node(node_name="guardrails_node")
def guardrails_node(state: dict[str, Any]) -> dict[str, Any]:
    draft = state.get("draft_response")
    citations = state.get("citations", [])
    retrieved_docs = state.get("retrieved_docs", [])

    status, violations = evaluate_guardrails(
        draft_response=draft,
        citations=citations,
        retrieved_docs=retrieved_docs,
    )

    if status == "PASSED":
        return {
            "guardrail_status": "PASSED",
            "guardrail_violations": [],
            "final_response": draft,
            "final_disposition": "AUTO_RESOLVED",
        }
    else:
        return {
            "guardrail_status": "TRIPPED",
            "guardrail_violations": violations,
            "final_response": None,
            "final_disposition": "ESCALATED_GUARDRAIL",
        }


@safe_node(node_name="escalate_node")
def escalate_node(state: dict[str, Any]) -> dict[str, Any]:
    snap = RunSnapshot.from_state(state)
    disp = snap.final_disposition if snap.was_set("final_disposition") else None

    if not disp or disp == "AUTO_RESOLVED":
        if snap.guardrail_status == "TRIPPED":
            disp = "ESCALATED_GUARDRAIL"
        elif snap.was_set("routing_action") and snap.routing_action == "ESCALATE":
            disp = "ESCALATED_ROUTER"
        else:
            disp = "ESCALATED_ERROR"

    packet = snap.to_escalation_packet(disp)

    return {
        "final_disposition": disp,
        "final_response": None,
        "citations": [],
        "escalation_packet": packet,
    }


@safe_node(node_name="audit_node")
def audit_node(state: dict[str, Any]) -> dict[str, Any]:
    snap = RunSnapshot.from_state(state)
    ticket = snap.canonical_ticket
    if not ticket:
        return {}

    record = snap.to_audit_record(elapsed_ms(snap.started_at))
    try:
        log_decision(record, db_path=state.get("db_path"))
    except Exception as e:
        print(
            f"AUDIT WRITE FAILED for ticket {ticket.ticket_id} (run {record['run_id']}): {e}",
            file=sys.stderr,
        )
        return {"is_degraded": True, "error_details": f"audit_node: {e}"}
    return {}

