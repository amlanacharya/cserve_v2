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


def offline_heuristic_classification(prompt_text: str) -> str:
    """Deterministic local keyword matching for intent and urgency."""
    text = prompt_text.lower()

    # Intent detection
    intent = "general_inquiry"
    if any(k in text for k in ["api key", "apikey", "secret key", "rotate key", "401 unauthorized"]):
        intent = "api_key_issue"
    elif any(k in text for k in ["mfa", "authenticator", "two-factor", "2fa", "credential", "password", "locked out"]):
        intent = "authentication_failure"
    elif any(k in text for k in ["sso", "saml", "identity provider", "okta"]):
        intent = "sso_configuration"
    elif any(k in text for k in ["invoice", "charge", "billing", "payment", "card", "refund", "subscription"]):
        intent = "billing_query"
    elif any(k in text for k in ["quota", "overage", "exceeded limit"]):
        intent = "quota_or_overage"
    elif any(k in text for k in ["rate limit", "429", "throttled", "too many requests"]):
        intent = "rate_limit"
    elif any(k in text for k in ["rollback", "rolled back"]):
        intent = "rollback_request"
    elif any(k in text for k in ["deployment", "deploy", "container", "health check", "crashloop", "build fail"]):
        intent = "deployment_failure"
    elif any(k in text for k in ["database", "postgres", "sql", "db connection"]):
        intent = "database_issue"
    elif any(k in text for k in ["slow", "latency", "timeout", "degradation", "lag"]):
        intent = "performance_degradation"
    elif any(k in text for k in ["security incident", "breach", "vulnerability", "exploit"]):
        intent = "security_incident"
    elif any(k in text for k in ["unclear", "follow up", "any update", "hello?"]):
        intent = "unclear_request"

    # Urgency detection
    urgency = "LOW"
    if any(k in text for k in ["production down", "outage", "disaster", "emergency", "critical", "breach"]):
        urgency = "CRITICAL"
    elif any(k in text for k in ["urgent", "blocking", "broken", "fails", "fail", "error", "high priority"]):
        urgency = "HIGH"
    elif any(k in text for k in ["issue", "problem", "help", "how do i", "cannot", "can't"]):
        urgency = "MEDIUM"

    output = {
        "inferred_intent": intent,
        "intent_alternatives": {},
        "urgency": urgency,
        "confidence": 0.50,
    }
    return json.dumps(output)


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

    # ==========================================
    # Tier 1: Primary - Groq API (OpenAI-compatible)
    # ==========================================
    if settings.groq_api_key:
        groq_model = model_override or (
            settings.groq_classify_model
            if task_type == "classification"
            else settings.groq_gen_model
        )
        client = OpenAI(
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key,
            timeout=settings.provider_request_timeout,
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
                return text.strip(), "groq"
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "429" in err_str or "rate limit" in err_str
                if is_rate_limit and attempt < settings.provider_max_retries:
                    retry_after = None
                    if hasattr(e, "response") and hasattr(e.response, "headers"):
                        retry_after = extract_retry_after(e.response.headers, settings.backoff_cap)
                    sleep_time = (
                        retry_after
                        if retry_after is not None
                        else compute_jittered_backoff(attempt, settings.backoff_base, settings.backoff_cap)
                    )
                    logger.warning(f"Groq 429 rate limit. Backing off {sleep_time:.2f}s (attempt {attempt+1})")
                    time.sleep(sleep_time)
                    continue
                logger.warning(f"Groq Tier 1 failed: {e}. Cascading to Tier 2...")
                break

    # ==========================================
    # Tier 2: Secondary - Google Gemini API
    # ==========================================
    if settings.gemini_api_key:
        gemini_model = settings.gemini_model
        gemini_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"
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
                    if resp.status_code == 429 and attempt < settings.provider_max_retries:
                        retry_after = extract_retry_after(resp.headers, settings.backoff_cap)
                        sleep_time = (
                            retry_after
                            if retry_after is not None
                            else compute_jittered_backoff(attempt, settings.backoff_base, settings.backoff_cap)
                        )
                        logger.warning(f"Gemini 429 rate limit. Backing off {sleep_time:.2f}s")
                        time.sleep(sleep_time)
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip(), "gemini"
            except Exception as e:
                logger.warning(f"Gemini Tier 2 failed: {e}. Cascading to Tier 3...")
                break

    # ==========================================
    # Tier 3: Tertiary - Offline Fail-Safe Engine
    # ==========================================
    if task_type == "classification":
        logger.info("Executing Offline Fail-Safe Classification Engine")
        return offline_heuristic_classification(user_prompt), "offline_mock"

    # For generation, offline fail-safe engine never generates speculative answers
    logger.info("Offline Fail-Safe: suppressing speculative answer generation")
    return "", "offline_mock"

