import json
from src.core.types import UNCLEAR_INTENT


def offline_heuristic_classification(prompt_text: str) -> str:
    """Deterministic local keyword matching for intent and urgency."""
    text = prompt_text.lower()

    # Intent detection
    intent = UNCLEAR_INTENT
    if any(k in text for k in ["api key", "apikey", "secret key", "rotate key", "401 unauthorized"]):
        intent = "api_key_issue"
    elif any(k in text for k in ["mfa", "authenticator", "two-factor", "2fa", "credential", "password", "locked out"]):
        intent = "authentication_failure"
    elif any(k in text for k in ["sso", "saml", "identity provider", "okta"]):
        intent = "sso_configuration"
    elif any(k in text for k in ["invoice", "charge", "billing", "payment", "card", "refund", "subscription"]):
        intent = "billing_query"
    elif any(k in text for k in ["quota", "overage", "exceeded limit"]):
        intent = "quota_or_overage"
    elif any(k in text for k in ["rate limit", "429", "throttled", "too many requests"]):
        intent = "rate_limit"
    elif any(k in text for k in ["rollback", "rolled back"]):
        intent = "rollback_request"
    elif any(k in text for k in ["deployment", "deploy", "container", "health check", "crashloop", "build fail"]):
        intent = "deployment_failure"
    elif any(k in text for k in ["database", "postgres", "sql", "db connection"]):
        intent = "database_issue"
    elif any(k in text for k in ["slow", "latency", "timeout", "degradation", "lag"]):
        intent = "performance_degradation"
    elif any(k in text for k in ["security incident", "breach", "vulnerability", "exploit"]):
        intent = "security_incident"

    # Urgency detection
    urgency = "LOW"
    if any(k in text for k in ["production down", "outage", "disaster", "emergency", "critical", "breach"]):
        urgency = "CRITICAL"
    elif any(k in text for k in ["urgent", "blocking", "broken", "fails", "fail", "error", "high priority"]):
        urgency = "HIGH"
    elif any(k in text for k in ["issue", "problem", "help", "how do i", "cannot", "can't"]):
        urgency = "MEDIUM"

    output = {
        "inferred_intent": intent,
        "intent_alternatives": {},
        "urgency": urgency,
        "confidence": 0.50,
    }
    return json.dumps(output)
