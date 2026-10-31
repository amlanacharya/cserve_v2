import re
from src.core.patterns import (
    API_KEY_PATTERN,
    BEARER_TOKEN_PATTERN,
    CC_CANDIDATE_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    is_luhn_valid,
)


def scan_pii(text: str) -> list[str]:
    """
    Scans a text draft for PII or sensitive credentials.
    Returns a list of diagnosed violation strings.
    """
    if not text:
        return []

    violations: list[str] = []

    # API Keys
    if API_KEY_PATTERN.search(text):
        violations.append("CREDENTIAL_API_KEY_DETECTED")

    # Bearer tokens
    if BEARER_TOKEN_PATTERN.search(text):
        violations.append("CREDENTIAL_BEARER_TOKEN_DETECTED")

    # Emails
    if EMAIL_PATTERN.search(text):
        violations.append("PII_EMAIL_DETECTED")

    # Phone numbers
    phone_matches = PHONE_PATTERN.finditer(text)
    for m in phone_matches:
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) >= 10:
            violations.append("PII_PHONE_DETECTED")
            break

    # Credit cards with Luhn check
    cc_matches = CC_CANDIDATE_PATTERN.finditer(text)
    for m in cc_matches:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and is_luhn_valid(digits):
            violations.append("PII_CREDIT_CARD_DETECTED")
            break

    return violations

