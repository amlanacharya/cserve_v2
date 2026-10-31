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

# The dataset's 21 intent labels are the classification vocabulary (issue #10).
INTENT_LABELS: tuple[str, ...] = (
    "api_key_issue",
    "authentication_failure",
    "account_access",
    "sso_configuration",
    "billing_query",
    "quota_or_overage",
    "deployment_failure",
    "rollback_request",
    "rate_limit",
    "performance_degradation",
    "database_issue",
    "security_incident",
    "compliance_request",
    "configuration_help",
    "integration_help",
    "webhook_issue",
    "data_residency",
    "data_export",
    "feature_request",
    "onboarding",
    "unclear_request",
)
# Unclassifiable text -> UNCLEAR_INTENT (a vocabulary label); classification failure -> UNKNOWN_INTENT.
UNCLEAR_INTENT = "unclear_request"
UNKNOWN_INTENT = "unknown"
OFFLINE_PROVIDER: Provider = "offline_mock"
ESCALATION_URGENCY: Urgency = "HIGH"


def sql_in_list(values: tuple[str, ...]) -> str:
    """Render values as a SQL IN-list body, e.g. 'a','b'."""
    return ",".join(f"'{v}'" for v in values)
