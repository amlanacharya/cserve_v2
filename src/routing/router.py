from typing import Literal
from src.core.types import OFFLINE_PROVIDER, Provider, RoutingAction, Urgency
from src.core.config import get_settings


def evaluate_route(
    confidence: float,
    top_retrieval_score: float,
    urgency: Urgency,
    must_not_auto_respond: bool,
    tau: float | None = None,
    sigma: float | None = None,
    provider_used: Provider | None = None,
    node_failure: str | None = None,
) -> tuple[RoutingAction, str]:
    """
    Deterministic dual-gate routing pure function:
    AUTO_RESPOND if:
      confidence >= tau (default 0.75) AND
      top_retrieval_score >= sigma (default 0.65) AND
      urgency != 'CRITICAL' AND
      NOT must_not_auto_respond

    Generates explainable audit reasoning naming every passing and failing condition.
    """
    settings = get_settings()
    tau_val = tau if tau is not None else settings.intent_confidence_threshold
    sigma_val = sigma if sigma is not None else settings.retrieval_similarity_floor

    reasons: list[str] = []
    failed_conditions: list[str] = []

    # Gate 1: Confidence
    if confidence < tau_val:
        failed_conditions.append(f"c={confidence:.2f}<{tau_val:.2f}")
    else:
        reasons.append(f"c={confidence:.2f}>={tau_val:.2f}")

    # Gate 2: Retrieval score
    if top_retrieval_score < sigma_val:
        failed_conditions.append(f"s_ret={top_retrieval_score:.2f}<{sigma_val:.2f}")
    else:
        reasons.append(f"s_ret={top_retrieval_score:.2f}>={sigma_val:.2f}")

    # Gate 3: Urgency
    if urgency.upper() == "CRITICAL":
        failed_conditions.append("urgency==CRITICAL")
    else:
        reasons.append(f"urgency={urgency}")

    # Gate 4: Safety veto
    if must_not_auto_respond:
        failed_conditions.append("must_not_auto_respond==True")
    else:
        reasons.append("safe=True")

    if node_failure or provider_used == OFFLINE_PROVIDER:
        action: RoutingAction = "ESCALATE"
        if node_failure:
            routing_reason = f"NODE_FAILURE: {node_failure}"
        else:
            routing_reason = "OFFLINE_FALLBACK: all network providers unavailable"
        if failed_conditions:
            routing_reason += " (" + "; ".join(failed_conditions) + ")"
    elif failed_conditions:
        action = "ESCALATE"
        routing_reason = "Escalated: " + "; ".join(failed_conditions)
    else:
        action = "AUTO_RESPOND"
        routing_reason = "Auto-respond eligible: " + ", ".join(reasons)

    return action, routing_reason

