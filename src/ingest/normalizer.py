import re
import uuid
from datetime import datetime, timezone
from typing import Any
from src.core.models import CanonicalTicket
from src.core.patterns import (  # noqa: F401  (re-exported for existing callers)
    API_KEY_PATTERN,
    BEARER_TOKEN_PATTERN,
    CC_CANDIDATE_PATTERN,
    EMAIL_PATTERN,
    HTML_TAG_PATTERN,
    PHONE_PATTERN,
    WHITESPACE_PATTERN,
    is_luhn_valid,
)


def redact_pii(text: str) -> str:
    """Scrub sensitive credentials and PII from text."""
    if not text:
        return text

    # Redact API keys first
    text = API_KEY_PATTERN.sub("[REDACTED_API_KEY]", text)

    # Redact Bearer tokens
    text = BEARER_TOKEN_PATTERN.sub("Bearer [REDACTED_TOKEN]", text)

    # Redact Credit Card numbers with Luhn check
    def replace_cc(match: re.Match) -> str:
        matched_str = match.group(0)
        digits_only = re.sub(r"\D", "", matched_str)
        if 13 <= len(digits_only) <= 19 and is_luhn_valid(digits_only):
            return "[REDACTED_CC]"
        return matched_str

    text = CC_CANDIDATE_PATTERN.sub(replace_cc, text)

    # Redact Emails
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)

    # Redact Phones (only if matches phone pattern and length reasonable)
    def replace_phone(match: re.Match) -> str:
        m_str = match.group(0).strip()
        digits_only = re.sub(r"\D", "", m_str)
        if len(digits_only) >= 10:
            return "[REDACTED_PHONE]"
        return m_str

    text = PHONE_PATTERN.sub(replace_phone, text)

    return text


def clean_text(text: str) -> str:
    """Strip HTML tags and collapse whitespace without corrupting technical identifiers."""
    if not text:
        return ""
    # Strip HTML tags
    text = HTML_TAG_PATTERN.sub(" ", text)
    # Collapse multiple whitespaces
    text = WHITESPACE_PATTERN.sub(" ", text).strip()
    return text


def parse_timestamp(ts_value: Any) -> datetime:
    """Parse various timestamp representations into UTC datetime."""
    if isinstance(ts_value, datetime):
        if ts_value.tzinfo is None:
            return ts_value.replace(tzinfo=timezone.utc)
        return ts_value.astimezone(timezone.utc)

    if isinstance(ts_value, str) and ts_value.strip():
        # Handle ISO-8601 strings
        clean_ts = ts_value.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(clean_ts)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass

    return datetime.now(timezone.utc)


def normalize_ticket(raw_payload: dict[str, Any]) -> CanonicalTicket:
    """
    Ingests and normalizes raw ticket payloads across email, chat, docs_comment, and forum channels.
    Redacts inbound PII and enforces the CanonicalTicket schema.
    """
    # 1. Determine channel
    channel = raw_payload.get("channel", "email").lower().strip()
    if channel not in ("email", "chat", "docs_comment", "forum"):
        channel = "email"

    # 2. Extract ticket_id
    ticket_id = str(raw_payload.get("ticket_id") or uuid.uuid4())

    # 3. Channel-specific field extraction
    subject: str | None = None
    body_raw: str = ""
    sender_ref: str | None = None
    metadata: dict[str, Any] = dict(raw_payload.get("metadata", {}))

    if channel == "email":
        subject = raw_payload.get("subject")
        body_raw = raw_payload.get("body") or raw_payload.get("email_body") or ""
        sender_ref = (
            raw_payload.get("from")
            or raw_payload.get("sender")
            or raw_payload.get("sender_ref")
            or raw_payload.get("customer_id")
            or raw_payload.get("customer_name")
        )
    elif channel == "chat":
        # Chat channels do not carry subjects
        subject = None
        body_raw = raw_payload.get("message") or raw_payload.get("body") or ""
        sender_ref = (
            raw_payload.get("user_id")
            or raw_payload.get("sender_ref")
            or raw_payload.get("customer_id")
            or raw_payload.get("customer_name")
        )
    elif channel == "docs_comment":
        # Docs comments do not carry subjects; preserve doc_id in metadata
        subject = None
        body_raw = raw_payload.get("comment_text") or raw_payload.get("body") or ""
        sender_ref = (
            raw_payload.get("user_id")
            or raw_payload.get("sender_ref")
            or raw_payload.get("customer_id")
            or raw_payload.get("customer_name")
        )
        if "doc_id" in raw_payload:
            metadata["doc_id"] = raw_payload["doc_id"]
    elif channel == "forum":
        subject = raw_payload.get("post_title") or raw_payload.get("subject")
        body_raw = raw_payload.get("post_content") or raw_payload.get("body") or ""
        sender_ref = (
            raw_payload.get("author")
            or raw_payload.get("sender_ref")
            or raw_payload.get("customer_id")
            or raw_payload.get("customer_name")
        )
        if "category" in raw_payload:
            metadata["category"] = raw_payload["category"]

    # Preserve any existing labels or customer info in metadata if present
    for extra_field in ("customer_tier", "customer_region", "language_fluency", "labels"):
        if extra_field in raw_payload and extra_field not in metadata:
            metadata[extra_field] = raw_payload[extra_field]

    # 4. Clean text and redact inbound PII
    cleaned_body = clean_text(body_raw)
    sanitized_body = redact_pii(cleaned_body)

    if subject:
        subject = clean_text(subject)
        subject = redact_pii(subject)

    # 5. Extract timestamp
    raw_ts = (
        raw_payload.get("received_at")
        or raw_payload.get("created_at")
        or raw_payload.get("timestamp")
    )
    created_at = parse_timestamp(raw_ts)

    return CanonicalTicket(
        ticket_id=ticket_id,
        channel=channel,  # type: ignore[arg-type]
        subject=subject,
        body=sanitized_body,
        sender_ref=str(sender_ref) if sender_ref is not None else None,
        created_at=created_at,
        metadata=metadata,
    )

