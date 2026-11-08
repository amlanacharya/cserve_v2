# Ingest Component

## Overview
The `ingest` package standardizes heterogeneous incoming support tickets from four communication channels (`email`, `chat`, `docs_comment`, and `forum`) into a unified `CanonicalTicket` model while enforcing inbound PII sanitization.

## Interface
- `[src/ingest/normalizer.py:normalize_ticket]`: `normalize_ticket(raw_payload: dict[str, Any]) -> CanonicalTicket` converts raw dictionary inputs into canonical ticket models.
- `[src/ingest/normalizer.py:normalize_ticket_with_stats]`: `normalize_ticket_with_stats(raw_payload: dict[str, Any]) -> tuple[CanonicalTicket, int]` normalizes payload and tallies inbound PII redactions.
- `[src/ingest/normalizer.py:redact_pii]`: `redact_pii(text: str) -> str` scrubs sensitive credentials, cards, emails, and phone numbers.
- `[src/ingest/normalizer.py:redact_pii_counted]`: `redact_pii_counted(text: str) -> tuple[str, int]` scrubs PII and returns replacement count.
- `[src/ingest/normalizer.py:clean_text]`: `clean_text(text: str) -> str` removes HTML markup and normalizes whitespace sequences.
- `[src/ingest/normalizer.py:parse_timestamp]`: `parse_timestamp(ts_value: Any) -> datetime` parses ISO-8601 strings into UTC datetime objects.

## Invariants
- `[src/ingest/normalizer.py:MISSING_TIMESTAMP]`: Missing or malformed timestamps are assigned `1970-01-01T00:00:00Z` rather than `datetime.now()` to preserve deterministic caching keys.
- `[src/ingest/normalizer.py:normalize_ticket_with_stats]`: Enforces channel constraints: `chat` and `docs_comment` tickets force `subject = None`; unrecognized channels default to `'email'`.
- `[src/ingest/normalizer.py:normalize_ticket_with_stats]`: All incoming bodies and subjects are scrubbed of PII prior to pipeline distribution.

## Side Effects
- None: pure transformation and sanitization logic.

## Verification
- Run: `pytest tests/unit/test_ingest.py -v`

