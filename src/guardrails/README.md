# Guardrails Component

## Overview
The `guardrails` package implements active safety verification on model-generated draft responses. It performs inbound and outbound PII scanning (API keys, bearer tokens, credit cards, emails, phone numbers) and lexical entailment validation to block hallucinated citations or ungrounded claims before delivery.

## Interface
- `[src/guardrails/__init__.py:evaluate_guardrails]`: `evaluate_guardrails(draft_response: str | None, citations: list[str], retrieved_docs: list[DocumentChunk]) -> tuple[Literal["PASSED", "TRIPPED"], list[str]]` evaluates comprehensive response safety.
- `[src/guardrails/pii.py:scan_pii]`: `scan_pii(text: str) -> list[str]` inspects text for sensitive credentials and customer PII.
- `[src/guardrails/hallucination.py:check_hallucination_and_entailment]`: `check_hallucination_and_entailment(draft_response: str, citations: list[str], retrieved_docs: list[DocumentChunk], min_entailment_ratio: float = 0.50) -> list[str]` verifies doc citations exist and checks lexical overlap.

## Invariants
- `[src/guardrails/__init__.py:evaluate_guardrails]`: Missing or empty draft text automatically evaluates to `"TRIPPED"` with `EMPTY_DRAFT_RESPONSE`.
- `[src/guardrails/hallucination.py:check_hallucination_and_entailment]`: Requires $\ge 1$ cited document, verifies all cited IDs exist in the retrieved context set, and mandates that every sentence achieves $\ge 50\%$ unigram overlap with the cited text.
- `[src/guardrails/pii.py:scan_pii]`: Credit card candidates must pass the Luhn algorithm (`is_card_number`), and phone candidates must contain $\ge 10$ digits to trigger tripping.

## Side Effects
- None: pure in-memory lexical analysis without external network, disk, or database side effects.

## Verification
- Run: `pytest tests/unit/test_guardrails.py -v`

