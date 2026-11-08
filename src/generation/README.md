# Generation Component

## Overview
The `generation` package handles prompt synthesis, context sandboxing, and inference execution across a resilient 3-tier cascade (Groq $\rightarrow$ Google Gemini $\rightarrow$ offline heuristic fail-safe engine). It enforces explicit XML tag demarcation and citation anchor formatting (`[DOC-ID]`).

## Interface
- `[src/generation/cascade.py:call_cascade]`: `call_cascade(system_prompt: str, user_prompt: str, temperature: float = 0.0, task_type: str = "generation", model_override: str | None = None) -> tuple[str, str]` executes Tier 1 (Groq), Tier 2 (Gemini), and Tier 3 (offline mock).
- `[src/generation/cascade.py:compute_jittered_backoff]`: `compute_jittered_backoff(attempt: int, base: float, cap: float) -> float` calculates uniform jittered exponential sleep duration.
- `[src/generation/cascade.py:extract_retry_after]`: `extract_retry_after(headers: Any, cap: float) -> float | None` parses and bounds HTTP `Retry-After` headers.
- `[src/generation/generator.py:generate_response]`: `generate_response(subject: str | None, body: str, retrieved_docs: list[DocumentChunk]) -> dict[str, Any]` packages top retrieval passages, runs inference, and returns draft text, citations, and provider.
- `[src/generation/generator.py:extract_citations]`: `extract_citations(text: str) -> list[str]` parses ordered, deduplicated `[DOC-ID]` citations.
- `[src/generation/generator.py:normalize_generated_text]`: `normalize_generated_text(text: str) -> str` fixes unicode typographic symbols and wraps bare documentation IDs in bracket anchors.
- `[src/generation/prompts.py:CLASSIFICATION_SYSTEM_PROMPT, GENERATION_SYSTEM_PROMPT]`: System prompts establishing strict grounding and output schemas.
- `[src/generation/prompts.py:escape_xml, format_classification_prompt, format_generation_prompt]`: Sanitization and prompt formatting utilities wrapping user data in XML delimiters.

## Invariants
- `[src/generation/cascade.py:_call_offline]`: During complete provider outages, the offline fail-safe engine suppresses generative drafting (`""`) to prevent hallucinated advice.
- `[src/generation/cascade.py:_call_groq]`: Sets SDK `max_retries=0` to guarantee all retry logic respects the global configuration budget (`provider_max_retries`) and full-jitter backoff caps.
- `[src/generation/prompts.py:escape_xml]`: User ticket content is strictly escaped to prevent delimiter-breaking prompt injection attacks.

## Side Effects
- `[src/generation/cascade.py:call_cascade]`: Dispatches HTTPS network requests to Groq and Gemini APIs.
- `[src/generation/cascade.py:_backoff_if_retryable]`: Pauses thread execution via `time.sleep` when encountering 429 rate limits or 5xx server errors.

## Verification
- Run: `pytest tests/unit/test_generation.py -v`

