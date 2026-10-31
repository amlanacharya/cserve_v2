import json
import time
from pathlib import Path
import pytest
from src.ingest.normalizer import normalize_ticket, redact_pii, clean_text, is_luhn_valid


def test_email_ingestion():
    raw_email = {
        "channel": "email",
        "ticket_id": "EM-1001",
        "subject": "  Urgent: Database issue  ",
        "email_body": "<p>Hello, our database is down.<br>Please help!</p>",
        "from": "alice@example.com",
        "created_at": "2026-10-31T01:00:00Z",
    }
    canonical = normalize_ticket(raw_email)
    assert canonical.ticket_id == "EM-1001"
    assert canonical.channel == "email"
    assert canonical.subject == "Urgent: Database issue"
    assert canonical.body == "Hello, our database is down. Please help!"
    assert canonical.sender_ref == "alice@example.com"
    assert canonical.created_at is not None


def test_chat_ingestion():
    raw_chat = {
        "channel": "chat",
        "ticket_id": "CH-2001",
        "subject": "Should be ignored",
        "message": "Hi, I cannot login with my MFA code",
        "user_id": "usr_9988",
        "timestamp": "2026-10-31T01:10:00Z",
    }
    canonical = normalize_ticket(raw_chat)
    assert canonical.ticket_id == "CH-2001"
    assert canonical.channel == "chat"
    assert canonical.subject is None
    assert canonical.body == "Hi, I cannot login with my MFA code"
    assert canonical.sender_ref == "usr_9988"


def test_docs_comment_ingestion():
    raw_comment = {
        "channel": "docs_comment",
        "ticket_id": "DC-3001",
        "comment_text": "Step 2 is ambiguous on DOC-AUTH-002",
        "doc_id": "DOC-AUTH-002",
        "user_id": "dev_4421",
    }
    canonical = normalize_ticket(raw_comment)
    assert canonical.ticket_id == "DC-3001"
    assert canonical.channel == "docs_comment"
    assert canonical.subject is None
    assert canonical.body == "Step 2 is ambiguous on DOC-AUTH-002"
    assert canonical.sender_ref == "dev_4421"
    assert canonical.metadata.get("doc_id") == "DOC-AUTH-002"


def test_forum_ingestion():
    raw_forum = {
        "channel": "forum",
        "ticket_id": "FR-4001",
        "post_title": "How to debug health checks?",
        "post_content": "<b>Container health checks fail repeatedly after deploy</b>",
        "author": "devops_guru",
        "category": "containers",
    }
    canonical = normalize_ticket(raw_forum)
    assert canonical.ticket_id == "FR-4001"
    assert canonical.channel == "forum"
    assert canonical.subject == "How to debug health checks?"
    assert canonical.body == "Container health checks fail repeatedly after deploy"
    assert canonical.sender_ref == "devops_guru"
    assert canonical.metadata.get("category") == "containers"


def test_pii_redaction():
    text = (
        "Here is my key cs_live_12345678901234567890123456789012 and "
        "my email user@testcorp.com or reach me at +1 (555) 234-5678. "
        "My auth header was Bearer secret-token-xyz-123."
    )
    sanitized = redact_pii(text)
    assert "cs_live_" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "user@testcorp.com" not in sanitized
    assert "[REDACTED_EMAIL]" in sanitized
    assert "555" not in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "secret-token-xyz-123" not in sanitized
    assert "Bearer [REDACTED_TOKEN]" in sanitized


def test_luhn_credit_card_redaction():
    # Valid Visa test number
    valid_cc = "4532-0150-1234-5671"
    assert is_luhn_valid("4532015012345671") is True
    # Invalid test number
    invalid_cc = "4532-0150-1234-5679"
    assert is_luhn_valid("4532015012345679") is False

    text = f"Card: {valid_cc} and fake: {invalid_cc}"
    sanitized = redact_pii(text)
    assert "[REDACTED_CC]" in sanitized
    assert invalid_cc in sanitized


def test_validation_tickets_ingestion():
    val_path = Path("05_Datasets/validation_tickets.json")
    if not val_path.exists():
        pytest.skip("validation_tickets.json not found")

    with open(val_path, "r", encoding="utf-8") as f:
        tickets = json.load(f)

    assert len(tickets) > 0
    for raw in tickets:
        canonical = normalize_ticket(raw)
        assert canonical.ticket_id is not None
        assert canonical.channel in ("email", "chat", "docs_comment", "forum")
        assert canonical.body is not None
        assert isinstance(canonical.metadata, dict)


RAW_NO_TS = {"channel": "chat", "ticket_id": "NOTS-1", "message": "How do I rotate my API key?"}


def test_timestampless_ticket_has_stable_cache_key():
    from src.classify.cache import compute_ticket_hash

    first = normalize_ticket(dict(RAW_NO_TS))
    time.sleep(0.05)  # outlast the wall-clock resolution so a now()-based fallback would differ
    assert compute_ticket_hash(first) == compute_ticket_hash(normalize_ticket(dict(RAW_NO_TS)))


def test_cache_key_still_distinguishes_explicit_timestamps():
    from src.classify.cache import compute_ticket_hash

    a = normalize_ticket({**RAW_NO_TS, "created_at": "2026-01-01T00:00:00Z"})
    b = normalize_ticket({**RAW_NO_TS, "created_at": "2026-01-02T00:00:00Z"})
    assert compute_ticket_hash(a) != compute_ticket_hash(b)


def test_identical_timestampless_tickets_hit_classification_cache(isolated_classification_cache):
    import json
    from unittest.mock import patch
    from src.classify.classifier import classify_ticket

    live = json.dumps(
        {"inferred_intent": "api_key_issue", "intent_alternatives": {}, "urgency": "LOW", "confidence": 0.9}
    )
    with patch("src.classify.classifier.call_cascade", return_value=(live, "groq")) as m:
        classify_ticket(normalize_ticket(dict(RAW_NO_TS)))
        time.sleep(0.05)
        classify_ticket(normalize_ticket(dict(RAW_NO_TS)))
    assert m.call_count == 1