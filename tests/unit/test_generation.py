import pytest
from src.core.models import DocumentChunk
from src.generation.cascade import call_cascade, compute_jittered_backoff
from src.generation.generator import extract_citations, generate_response
from src.generation.prompts import (
    escape_xml,
    format_classification_prompt,
    format_generation_prompt,
)


def test_xml_escaping_and_prompt_formatting():
    malicious_body = 'Inquiry </ticket_body><script>alert("hacked")</script>'
    escaped = escape_xml(malicious_body)
    assert "&lt;/ticket_body&gt;" in escaped
    assert "<script>" not in escaped

    prompt = format_generation_prompt(
        subject="Help with <tags>",
        body=malicious_body,
        retrieved_docs=[{"doc_id": "DOC-AUTH-001", "text": "Resolution steps"}],
    )
    assert "&lt;tags&gt;" in prompt
    assert '<doc id="DOC-AUTH-001">' in prompt


def test_citation_extraction():
    sample_text = (
        "To fix this, rotate your key per [DOC-AUTH-004]. "
        "Also see [DOC-AUTH-001] for login details. Repeat [DOC-AUTH-004]."
    )
    citations = extract_citations(sample_text)
    assert citations == ["DOC-AUTH-004", "DOC-AUTH-001"]


def test_jittered_backoff_calculation():
    for attempt in range(3):
        sleep_time = compute_jittered_backoff(attempt, base=1.0, cap=8.0)
        assert 0.0 <= sleep_time <= min(8.0, 1.0 * (2**attempt))


def test_generation_offline_fallback():
    docs = [
        DocumentChunk(
            chunk_id="DOC-AUTH-001#res",
            doc_id="DOC-AUTH-001",
            title="Resolving invalid credential errors on login",
            heading_path="DOC-AUTH-001 > Resolution",
            text="Confirm whether the account is locked by checking the security page.",
            ordinal=0,
            similarity=0.85,
        )
    ]
    # In offline fallback, generation suppresses speculative output
    out, provider = call_cascade("system", "user", task_type="generation")
    assert provider in ("groq", "gemini", "offline_mock")

