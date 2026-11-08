# Core Component

## Overview
The `core` package defines shared domain models, environment configurations, literal type vocabularies, and regex pattern primitives used across all CloudServe processing stages.

## Interface
- `[src/core/config.py:Settings]`: Configuration schema reading environment variables for API keys, model designations, threshold gates, timeouts, and filesystem paths.
- `[src/core/config.py:get_settings]`: `get_settings() -> Settings` cached singleton accessor.
- `[src/core/models.py:CanonicalTicket]`: Pydantic schema for normalized customer inquiries across all supported channels.
- `[src/core/models.py:DocumentChunk]`: Schema representing indexed documentation passages with section hierarchies.
- `[src/core/models.py:EscalationPacket]`: Schema encapsulating enriched context for deflected/escalated tickets.
- `[src/core/models.py:ProcessedTicketResult]`: Final response contract returned to API and batch evaluation callers.
- `[src/core/patterns.py:API_KEY_PATTERN, BEARER_TOKEN_PATTERN, EMAIL_PATTERN, PHONE_PATTERN, CC_CANDIDATE_PATTERN]`: Regex pattern constants for identifying PII and secrets.
- `[src/core/patterns.py:is_card_number, is_phone_number, is_luhn_valid]`: Helper functions validating credit card Luhn checksums and telephone digit lengths.
- `[src/core/types.py:Urgency, Disposition, EscalatedDisposition, Provider, RoutingAction, GuardrailStatus]`: Domain literal type annotations and their runtime value tuples (`URGENCIES`, `DISPOSITIONS`, `PROVIDERS`).
- `[src/core/types.py:INTENT_LABELS, UNCLEAR_INTENT, UNKNOWN_INTENT]`: 21-intent classification vocabulary and fallback sentinels.
- `[src/core/types.py:sql_in_list]`: `sql_in_list(values: tuple[str, ...]) -> str` formats literal tuples into SQL-compatible IN-list strings.

## Invariants
- `[src/core/config.py:Settings]`: System gates default to confidence threshold $\tau = 0.75$, retrieval floor $\sigma = 0.65$, `top_k_passages = 3`, and `top_k_escalate = 2`.
- `[src/core/patterns.py:is_luhn_valid]`: Rejects digit strings shorter than 13 or longer than 19 digits; verifies standard Luhn mod-10 formula.
- `[src/core/types.py:INTENT_LABELS]`: Canonical 21-label intent taxonomy enforced across classifiers and routing nodes.

## Side Effects
- `[src/core/config.py:load_dotenv]`: Reads environment variables from `.env` file on disk at import time.

## Verification
- Run: `pytest tests/unit/test_routing.py tests/unit/test_ingest.py -v`

