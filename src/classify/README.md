# Classify Component

## Overview
The `classify` package categorizes incoming customer support inquiries by intent and urgency, estimates confidence scores, identifies alternative intent hypotheses, and enforces non-negotiable safety veto triggers (such as billing refunds, legal threats, and human escalations).

## Interface
- `[src/classify/classifier.py:classify_ticket]`: `classify_ticket(ticket: CanonicalTicket) -> dict[str, Any]` processes a canonical ticket to produce inferred intent, alternatives, urgency, confidence, and safety veto flags.
- `[src/classify/classifier.py:extract_json_from_llm_output]`: `extract_json_from_llm_output(text: str) -> dict[str, Any]` parses raw LLM generation into a dictionary.
- `[src/classify/cache.py:ClassificationCache]`: Caching layer backed by in-memory dictionary and disk-persisted JSON file.
- `[src/classify/cache.py:compute_ticket_hash]`: `compute_ticket_hash(ticket: CanonicalTicket) -> str` generates a deterministic SHA-256 digest from a serialized ticket.
- `[src/classify/cache.py:get_classification_cache]`: `get_classification_cache() -> ClassificationCache` returns the global cache instance.
- `[src/classify/heuristic.py:offline_heuristic_classification]`: `offline_heuristic_classification(prompt_text: str) -> str` evaluates deterministic keyword matching when remote LLM providers are unavailable.

## Invariants
- `[src/classify/classifier.py:SAFETY_VETO_PATTERN]`: Any ticket matching sensitive keywords (refund, billing adjustment, legal action, security breach, human agent requests) forces `must_not_auto_respond = True`.
- `[src/classify/classifier.py:classify_ticket]`: When the offline fail-safe provider is active (`provider_used == OFFLINE_PROVIDER`), `must_not_auto_respond` is forced to `True` and results are never saved to disk cache.
- `[src/classify/classifier.py:classify_ticket]`: Inferred intents outside `INTENT_LABELS` are coerced to `UNKNOWN_INTENT` (`'unknown'`), and confidence is clamped between `0.0` and `1.0`.

## Side Effects
- `[src/classify/classifier.py:classify_ticket]`: Invokes `call_cascade`, performing outbound HTTPS network calls to LLM providers (Groq / Gemini).
- `[src/classify/cache.py:ClassificationCache.set]`: Writes cache updates to `data/cache/classification_cache.json` on disk.

## Verification
- Run: `pytest tests/unit/test_classify.py -v`

