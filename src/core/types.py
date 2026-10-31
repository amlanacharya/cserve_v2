"""Shared domain vocabularies: one definition each of urgency, disposition, provider."""
from typing import Literal, get_args

Urgency = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
EscalatedDisposition = Literal["ESCALATED_ROUTER", "ESCALATED_GUARDRAIL", "ESCALATED_ERROR"]
Disposition = Literal["AUTO_RESOLVED", "ESCALATED_ROUTER", "ESCALATED_GUARDRAIL", "ESCALATED_ERROR"]
Provider = Literal["groq", "gemini", "offline_mock"]
RoutingAction = Literal["AUTO_RESPOND", "ESCALATE"]
GuardrailStatus = Literal["PASSED", "TRIPPED"]

URGENCIES: tuple[str, ...] = get_args(Urgency)
DISPOSITIONS: tuple[str, ...] = get_args(Disposition)
PROVIDERS: tuple[str, ...] = get_args(Provider)

DEFAULT_URGENCY: Urgency = "MEDIUM"
OFFLINE_PROVIDER: Provider = "offline_mock"


def sql_in_list(values: tuple[str, ...]) -> str:
    """Render values as a SQL IN-list body, e.g. 'a','b'."""
    return ",".join(f"'{v}'" for v in values)
