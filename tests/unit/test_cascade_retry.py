"""Provider retry and failover (spec section 1 / 11) proven through a mocked httpx transport."""
from functools import partial
from types import SimpleNamespace

import httpx
import pytest
from openai import OpenAI

from src.generation import cascade

GROQ_OK = {"choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "groq-ok"}}],
           "id": "x", "object": "chat.completion", "created": 0, "model": "m"}
GEMINI_OK = {"candidates": [{"content": {"parts": [{"text": "gemini-ok"}]}}]}


def _settings():
    return SimpleNamespace(
        groq_api_key="k", groq_base_url="https://groq.test/v1", groq_gen_model="g", groq_classify_model="g",
        gemini_api_key="k", gemini_model="gm", provider_request_timeout=1.0,
        provider_max_retries=1, backoff_base=1.0, backoff_cap=8.0,
    )


@pytest.fixture
def harness(monkeypatch):
    """Returns (calls, sleeps, handlers); handlers maps provider -> fn(request, call_number)."""
    calls = {"groq": 0, "gemini": 0}
    sleeps = []
    handlers = {}

    def transport_for(name):
        def handle(request):
            calls[name] += 1
            return handlers[name](request, calls[name])
        return httpx.MockTransport(handle)

    real_client = httpx.Client
    monkeypatch.setattr(cascade, "OpenAI", partial(OpenAI, http_client=real_client(transport=transport_for("groq"))))
    fake_httpx = SimpleNamespace(**vars(httpx))
    fake_httpx.Client = lambda **kw: real_client(transport=transport_for("gemini"), **kw)
    monkeypatch.setattr(cascade, "httpx", fake_httpx)
    monkeypatch.setattr(cascade, "get_settings", _settings)
    monkeypatch.setattr(cascade.time, "sleep", sleeps.append)
    return calls, sleeps, handlers


def _err(status, headers=None):
    return lambda req, n: httpx.Response(status, json={"error": "x"}, headers=headers or {})


def _timeout(req, n):
    raise httpx.ReadTimeout("slow", request=req)


@pytest.mark.parametrize("fail", [_err(500), _err(429), _timeout], ids=["5xx", "429", "timeout"])
def test_each_failure_kind_retries_once_then_succeeds(harness, fail):
    calls, sleeps, h = harness
    h["groq"] = lambda req, n: fail(req, n) if n == 1 else httpx.Response(200, json=GROQ_OK)
    text, provider = cascade.call_cascade("s", "u")
    assert (text, provider) == ("groq-ok", "groq")
    assert calls["groq"] == 2 and len(sleeps) == 1


@pytest.mark.parametrize("fail", [_err(500), _err(429), _timeout], ids=["5xx", "429", "timeout"])
def test_retries_are_bounded_with_no_hidden_sdk_retries(harness, fail):
    calls, _, h = harness
    h["groq"] = fail
    h["gemini"] = lambda req, n: httpx.Response(200, json=GEMINI_OK)
    cascade.call_cascade("s", "u")
    assert calls["groq"] == 2  # 1 + provider_max_retries; SDK default would make 3


def test_retry_after_header_is_honoured(harness):
    calls, sleeps, h = harness
    h["groq"] = lambda req, n: (
        httpx.Response(429, headers={"Retry-After": "3"}) if n == 1 else httpx.Response(200, json=GROQ_OK)
    )
    cascade.call_cascade("s", "u")
    assert sleeps == [3.0]


def test_failover_groq_to_gemini(harness):
    calls, _, h = harness
    h["groq"] = _err(503)
    h["gemini"] = lambda req, n: httpx.Response(200, json=GEMINI_OK)
    assert cascade.call_cascade("s", "u") == ("gemini-ok", "gemini")
    assert calls == {"groq": 2, "gemini": 1}


def test_gemini_retries_5xx_and_timeouts(harness):
    calls, _, h = harness
    h["groq"] = _err(500)
    h["gemini"] = lambda req, n: _timeout(req, n) if n == 1 else httpx.Response(200, json=GEMINI_OK)
    assert cascade.call_cascade("s", "u")[1] == "gemini"
    assert calls["gemini"] == 2


def test_failover_groq_to_gemini_to_offline(harness):
    calls, _, h = harness
    h["groq"] = _err(500)
    h["gemini"] = _err(429)
    text, provider = cascade.call_cascade("s", "api key 401", task_type="classification")
    assert provider == "offline_mock" and "api_key_issue" in text
    assert calls == {"groq": 2, "gemini": 2}
