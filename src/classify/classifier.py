import json
import logging
import re
from typing import Any
from src.classify.cache import compute_ticket_hash, get_classification_cache
from src.core.models import CanonicalTicket
from src.core.types import URGENCIES
from src.generation.cascade import call_cascade
from src.generation.prompts import (
    CLASSIFICATION_SYSTEM_PROMPT,
    format_classification_prompt,
)

logger = logging.getLogger(__name__)

SAFETY_VETO_PATTERN = re.compile(
    r"\b(refund|billing\s+adjustment|delete\s+my\s+account|legal\s+action|attorney|subpoena"
    r"|security\s+vulnerability|breach|exploit|talk\s+to\s+a\s+human"
    r"|(?:human|live|real|support|customer\s+service)\s+agent"
    r"|(?:talk|speak|transfer(?:\s+me)?|escalate)\s+(?:to|with)\s+an?\s+agent)\b",
    re.IGNORECASE,
)


def extract_json_from_llm_output(text: str) -> dict[str, Any]:
    """Strips Markdown fences and parses JSON payload."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        # Fallback regex search for JSON object
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Could not parse valid JSON from response: {text}")


def classify_ticket(ticket: CanonicalTicket) -> dict[str, Any]:
    """
    Classifies a CanonicalTicket's intent, urgency, alternatives, and confidence.
    Enforces safety veto rules and utilizes the classification cache.
    """
    ticket_hash = compute_ticket_hash(ticket)
    cache = get_classification_cache()

    cached_res = cache.get(ticket_hash)
    if cached_res is not None:
        return cached_res

    # 1. Evaluate Safety Veto
    combined_text = f"{ticket.subject or ''} {ticket.body}"
    safety_veto = bool(SAFETY_VETO_PATTERN.search(combined_text))

    # 2. Invoke cascade
    user_prompt = format_classification_prompt(ticket.subject, ticket.body)
    raw_response, provider_used = call_cascade(
        system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.0,
        task_type="classification",
    )

    # 3. Parse JSON
    try:
        parsed = extract_json_from_llm_output(raw_response)
        inferred_intent = str(parsed.get("inferred_intent", "general_inquiry")).strip()
        intent_alternatives = dict(parsed.get("intent_alternatives", {}))
        urgency = str(parsed.get("urgency", "MEDIUM")).strip().upper()
        if urgency not in URGENCIES:
            urgency = "MEDIUM"
        confidence = float(parsed.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
    except Exception as e:
        logger.warning(f"Classification JSON parsing failed: {e}. Using fallback defaults.")
        inferred_intent = "unknown"
        intent_alternatives = {}
        urgency = "HIGH"
        confidence = 0.0

    # Offline mock always vetoes auto response
    if provider_used == "offline_mock":
        safety_veto = True

    result = {
        "inferred_intent": inferred_intent,
        "intent_alternatives": intent_alternatives,
        "urgency": urgency,
        "confidence": round(confidence, 4),
        "must_not_auto_respond": safety_veto,
        "provider_used": provider_used,
    }

    # Offline fail-safe results must never be replayed after providers recover
    if provider_used != "offline_mock":
        cache.set(ticket_hash, result)
    return result

