import functools
import logging
import traceback
from typing import Any, Callable
from src.core.models import CanonicalTicket

logger = logging.getLogger(__name__)


def safe_node(node_name: str, fallback_action: str = ""):
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
                    "error_details": f"{node_name}: {traceback.format_exc()}",
                }

                if node_name == "normalize_node":
                    raw = state.get("raw_ticket", {})
                    updates["canonical_ticket"] = CanonicalTicket(
                        ticket_id=str(raw.get("ticket_id", "FALLBACK-ID")),
                        channel="email",
                        body=str(raw.get("body", "")),
                    )

                elif node_name == "classify_node":
                    updates.update(
                        {
                            "inferred_intent": "unknown",
                            "confidence": 0.0,
                            "intent_alternatives": {},
                            "urgency": "HIGH",
                            "must_not_auto_respond": True,
                            "provider_used": "offline_mock",
                        }
                    )

                elif node_name == "retrieval_node":
                    updates.update(
                        {
                            "retrieved_docs": [],
                            "top_retrieval_score": 0.0,
                        }
                    )

                elif node_name == "routing_node":
                    updates.update(
                        {
                            "routing_action": "ESCALATE",
                            "routing_reason": f"Routing node fault diversion: {str(e)}",
                        }
                    )

                elif node_name == "generation_node":
                    updates.update(
                        {
                            "draft_response": None,
                            "citations": [],
                            "final_disposition": "ESCALATED_ERROR",
                        }
                    )

                elif node_name == "guardrails_node":
                    updates.update(
                        {
                            "guardrail_status": "TRIPPED",
                            "guardrail_violations": [f"Guardrail execution failure: {str(e)}"],
                            "final_disposition": "ESCALATED_GUARDRAIL",
                        }
                    )

                elif node_name == "escalate_node":
                    updates.update(
                        {
                            "final_disposition": "ESCALATED_ERROR",
                        }
                    )

                elif node_name == "audit_node":
                    # Audit failure must not crash pipeline
                    pass

                # Return merged updates into state
                return updates

        return wrapper

    return decorator

