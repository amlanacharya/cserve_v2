import json
import logging
import random
import re
import time
from typing import Any
import httpx
from openai import OpenAI
from src.core.config import get_settings

logger = logging.getLogger(__name__)


def compute_jittered_backoff(attempt: int, base: float, cap: float) -> float:
    """Exponential backoff with full jitter: sleep ~ U(0, min(cap, base * 2^attempt))."""
    max_sleep = min(cap, base * (2**attempt))
    return random.uniform(0, max_sleep)


def extract_retry_after(headers: Any, cap: float) -> float | None:
    """Extracts and clamps Retry-After header if present."""
    if not headers:
        return None
    val = headers.get("retry-after") or headers.get("Retry-After")
    if val:
        try:
            return min(float(val), cap)
        except ValueError:
            pass
    return None


def _retryable_response(exc: Exception) -> Any:
    """Returns the HTTP response (or None) if exc is a timeout, 5xx or 429; else False."""
    if isinstance(exc, httpx.TimeoutException) or type(exc).__name__ == "APITimeoutError":
        return None
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status is not None and (status == 429 or status >= 500):
        return response
    return False


def _backoff_if_retryable(provider: str, exc: Exception, attempt: int, settings: Any) -> bool:
    """Sleeps (Retry-After or jittered backoff) and returns True if the failure may be retried."""
    if attempt >= settings.provider_max_retries:
        return False
    response = _retryable_response(exc)
    if response is False:
        return False
    retry_after = extract_retry_after(getattr(response, "headers", None), settings.backoff_cap)
    sleep_time = (
        retry_after
        if retry_after is not None
        else compute_jittered_backoff(attempt, settings.backoff_base, settings.backoff_cap)
    )
    logger.warning(f"{provider} retryable failure ({exc}). Backing off {sleep_time:.2f}s (attempt {attempt+1})")
    time.sleep(sleep_time)
    return True


def _call_groq(
    settings: Any, system_prompt: str, user_prompt: str, temperature: float, task_type: str, model_override: str | None
) -> str | None:
    """Tier 1: Groq (OpenAI-compatible). Returns text, or None to cascade."""
    groq_model = model_override or (
        settings.groq_classify_model if task_type == "classification" else settings.groq_gen_model
    )
    client = OpenAI(
        base_url=settings.groq_base_url,
        api_key=settings.groq_api_key,
        timeout=settings.provider_request_timeout,
        max_retries=0,  # retry budget is ours (spec 1); no hidden SDK retries
    )

    for attempt in range(settings.provider_max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            text = response.choices[0].message.content or ""
            return text.strip()
        except Exception as e:
            if _backoff_if_retryable("Groq", e, attempt, settings):
                continue
            logger.warning(f"Groq Tier 1 failed: {e}. Cascading to Tier 2...")
            break
    return None


def _call_gemini(settings: Any, system_prompt: str, user_prompt: str, temperature: float) -> str | None:
    """Tier 2: Google Gemini. Returns text, or None to cascade."""
    gemini_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    gemini_payload = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"temperature": temperature},
    }

    for attempt in range(settings.provider_max_retries + 1):
        try:
            with httpx.Client(timeout=settings.provider_request_timeout) as http_client:
                resp = http_client.post(gemini_url, json=gemini_payload)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
        except Exception as e:
            if _backoff_if_retryable("Gemini", e, attempt, settings):
                continue
            logger.warning(f"Gemini Tier 2 failed: {e}. Cascading to Tier 3...")
            break
    return None


def _call_offline(user_prompt: str, task_type: str) -> tuple[str, str]:
    """Tier 3: offline fail-safe."""
    if task_type == "classification":
        logger.info("Executing Offline Fail-Safe Classification Engine")
        # Lazy import: classify.classifier imports this module.
        from src.classify.heuristic import offline_heuristic_classification

        return offline_heuristic_classification(user_prompt), "offline_mock"

    # For generation, offline fail-safe engine never generates speculative answers
    logger.info("Offline Fail-Safe: suppressing speculative answer generation")
    return "", "offline_mock"


def call_cascade(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    task_type: str = "generation",
    model_override: str | None = None,
) -> tuple[str, str]:
    """
    Executes inference cascade:
    Tier 1: Groq API
    Tier 2: Google Gemini API
    Tier 3: Offline fail-safe heuristic engine
    Returns: (output_text, provider_used)
    """
    settings = get_settings()

    if settings.groq_api_key:
        text = _call_groq(settings, system_prompt, user_prompt, temperature, task_type, model_override)
        if text is not None:
            return text, "groq"

    if settings.gemini_api_key:
        text = _call_gemini(settings, system_prompt, user_prompt, temperature)
        if text is not None:
            return text, "gemini"

    return _call_offline(user_prompt, task_type)
