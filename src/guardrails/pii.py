from src.core.patterns import (
    API_KEY_PATTERN,
    BEARER_TOKEN_PATTERN,
    CC_CANDIDATE_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    is_card_number,
    is_phone_number,
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
    if any(is_phone_number(m.group(0)) for m in PHONE_PATTERN.finditer(text)):
        violations.append("PII_PHONE_DETECTED")

    # Credit cards with Luhn check
    if any(is_card_number(m.group(0)) for m in CC_CANDIDATE_PATTERN.finditer(text)):
        violations.append("PII_CREDIT_CARD_DETECTED")

    return violations

