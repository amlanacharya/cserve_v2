import json
import pytest
from src.classify.cache import ClassificationCache, compute_ticket_hash
from src.classify.classifier import (
    SAFETY_VETO_PATTERN,
    classify_ticket,
    extract_json_from_llm_output,
)
from src.core.models import CanonicalTicket


def test_safety_veto_patterns():
    veto_phrases = [
        "I demand a refund immediately",
        "Please provide a billing adjustment for last month",
        "Delete my account permanently",
        "We are taking legal action with our attorney",
        "Responding to a court subpoena",
        "Found a critical security vulnerability and active exploit",
        "I need to talk to a human agent right now",
    ]
    for phrase in veto_phrases:
        assert bool(SAFETY_VETO_PATTERN.search(phrase)) is True

    safe_phrases = [
        "How do I rotate an API key?",
        "My container fails during health checks",
        "Where can I find SSO documentation?",
    ]
    for phrase in safe_phrases:
        assert bool(SAFETY_VETO_PATTERN.search(phrase)) is False


@pytest.mark.parametrize(
    "text,expected",
    [
        ("What is my user agent string?", False),
        ("Does it support multiple agents?", False),
        ("The agent SDK fails to install", False),
        ("Rebreach of the target is fine", False),
        ("Refund me now", True),
        ("I need to talk to a human", True),
        ("Get me a human agent", True),
        ("I want a live agent", True),
        ("Transfer me to an agent please", True),
        ("We found a breach", True),
    ],
)
def test_safety_veto_precision(text, expected):
    assert bool(SAFETY_VETO_PATTERN.search(text)) is expected


def test_extract_json_from_llm_output():
    raw_markdown = """```json
    {
      "inferred_intent": "api_key_issue",
      "intent_alternatives": {"auth_issue": 0.2},
      "urgency": "MEDIUM",
      "confidence": 0.88
    }
    ```"""
    parsed = extract_json_from_llm_output(raw_markdown)
    assert parsed["inferred_intent"] == "api_key_issue"
    assert parsed["confidence"] == 0.88


def test_classification_offline_fallback():
    ticket = CanonicalTicket(
        ticket_id="TEST-CLS-01",
        channel="chat",
        subject=None,
        body="One of our production keys started returning 401 Unauthorized after rotate key",
    )
    # Even if offline mock runs, it should extract intent correctly
    res = classify_ticket(ticket)
    assert res["inferred_intent"] in ("api_key_issue", "authentication_failure")
    assert res["confidence"] >= 0.0
    assert res["urgency"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert "must_not_auto_respond" in res


def test_classification_caching(tmp_path):
    cache = ClassificationCache(tmp_path / "cache.json")
    ticket = CanonicalTicket(
        ticket_id="TEST-CLS-02",
        channel="email",
        subject="Invoice inquiry",
        body="Can I get an invoice copy for April?",
    )
    thash = compute_ticket_hash(ticket)
    assert cache.get(thash) is None

    mock_result = {
        "inferred_intent": "billing_query",
        "intent_alternatives": {},
        "urgency": "LOW",
        "confidence": 0.95,
        "must_not_auto_respond": False,
        "provider_used": "groq",
    }
    cache.set(thash, mock_result)
    assert cache.get(thash) == mock_result

