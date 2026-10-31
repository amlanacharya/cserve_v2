"""Shared PII/credential patterns and helpers (used by ingest and guardrails)."""
import re

# Regular expression patterns for PII and sensitive data
API_KEY_PATTERN = re.compile(r"cs_live_[0-9a-zA-Z]{32}")
BEARER_TOKEN_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(
    r"(?:(?:\+?1\s*(?:[.-]\s*)?)?(?:\(\s*([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9])\s*\)|([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9]))\s*(?:[.-]\s*)?)?([2-9]1[02-9]|[2-9][02-9]1|[2-9][02-9]{2})\s*(?:[.-]\s*)?([0-9]{4})(?:\s*(?:#|x\.?|ext\.?|extension)\s*(\d+))?"
)
CC_CANDIDATE_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


def is_card_number(candidate: str) -> bool:
    """True if the matched text is a 13-19 digit, Luhn-valid card number."""
    digits = re.sub(r"\D", "", candidate)
    return 13 <= len(digits) <= 19 and is_luhn_valid(digits)


def is_phone_number(candidate: str) -> bool:
    """True if the matched text carries at least 10 digits (PHONE_PATTERN also matches shorter runs)."""
    return len(re.sub(r"\D", "", candidate)) >= 10


def is_luhn_valid(candidate: str) -> bool:
    digits = [int(c) for c in candidate if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0
