import functools
import logging
import traceback
from typing import Any, Callable
from src.core.models import CanonicalTicket
from src.core.types import ESCALATION_URGENCY, OFFLINE_PROVIDER, UNKNOWN_INTENT
from src.ingest.normalizer import redact_pii_counted

logger = logging.getLogger(__name__)


def _normalize_fallback(state: dict[str, Any], exc: Exception) -> dict[str, Any]:
    raw = state.get("raw_ticket", {})
    channel = str(raw.get("channel", "email")).lower().strip()
    if channel not in ("email", "chat", "docs_comment", "forum"):
        channel = "email"
    # The fallback body must not leak raw PII downstream, and the audit must still count it.
    body, redactions = redact_pii_counted(str(raw.get("body", "")))
    return {
        "canonical_ticket": CanonicalTicket(
            ticket_id=str(raw.get("ticket_id", "FALLBACK-ID")),
            channel=channel,  # type: ignore[arg-type]
            body=body,
        ),
        "pii_redactions_count": redactions,
    }


# Per-node safe defaults applied when a node raises. audit_node (and unknown
# nodes) intentionally have none: an audit failure must not crash the pipeline.
_FALLBACKS: dict[str, Callable[[dict[str, Any], Exception], dict[str, Any]]] = {
    "normalize_node": _normalize_fallback,
    "classify_node": lambda s, e: {
        "inferred_intent": UNKNOWN_INTENT,
        "confidence": 0.0,
        "intent_alternatives": {},
        "urgency": ESCALATION_URGENCY,
        "must_not_auto_respond": True,
        "provider_used": OFFLINE_PROVIDER,
        # No tier classified this ticket: leave classification_provider unset so the audit row
        # is NULL there and per-provider metrics bucket it as a classify failure, not offline_mock.
        "classification_provider": None,
        "failed_node": "classify_node",
    },
    # failed_node drives routing (first crash wins); failed_nodes (set by safe_node) is the audit trail.
    "retrieval_node": lambda s, e: {
        "retrieved_docs": [],
        "top_retrieval_score": 0.0,
        "failed_node": s.get("failed_node") or "retrieval_node",
    },
    "routing_node": lambda s, e: {
        "routing_action": "ESCALATE",
        "routing_reason": f"Routing node fault diversion: {str(e)}",
    },
    "generation_node": lambda s, e: {
        "draft_response": None,
        "citations": [],
        "final_disposition": "ESCALATED_ERROR",
    },
    "guardrails_node": lambda s, e: {
        "guardrail_status": "TRIPPED",
        "guardrail_violations": [f"Guardrail execution failure: {str(e)}"],
        "final_disposition": "ESCALATED_GUARDRAIL",
    },
    "escalate_node": lambda s, e: {"final_disposition": "ESCALATED_ERROR"},
}


def safe_node(node_name: str):
    """
    Decorator that catches all unhandled exceptions within a LangGraph node,
    records the failure in state and error logs, and sets safe default values
    so execution progresses cleanly to END without aborting the process (A11).
    """

    def decorator(fn: Callable[[dict[str, Any]], dict[str, Any]]):
        @functools.wraps(fn)
        def wrapper(state: dict[str, Any]) -> dict[str, Any]:
            try:
                return fn(state)
            except Exception as e:
                err_msg = f"Exception in {node_name}: {str(e)}"
                logger.error(err_msg, exc_info=True)
                updates: dict[str, Any] = {
                    "is_degraded": True,
                    "failed_nodes": [*state.get("failed_nodes", []), node_name],
                    "error_details": f"{node_name}: {traceback.format_exc()}",
                }

                fallback = _FALLBACKS.get(node_name)
                if fallback is not None:
                    updates.update(fallback(state, e))

                # Return merged updates into state
                return updates

        return wrapper

    return decorator

