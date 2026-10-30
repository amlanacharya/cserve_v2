import pytest
from src.core.models import DocumentChunk
from src.guardrails import evaluate_guardrails
from src.guardrails.hallucination import check_hallucination_and_entailment
from src.guardrails.pii import scan_pii


@pytest.fixture
def sample_retrieved_docs():
    return [
        DocumentChunk(
            chunk_id="DOC-AUTH-001#res",
            doc_id="DOC-AUTH-001",
            title="Resolving invalid credential errors on login",
            heading_path="DOC-AUTH-001 > Resolution",
            text="Confirm whether the account is locked by checking the security page. Clear browser cookies and cache.",
            ordinal=0,
            similarity=0.88,
        )
    ]


def test_pii_guardrail_detection():
    clean_text = "To resolve the issue, clear your cookies and retry."
    assert scan_pii(clean_text) == []

    dirty_text = "Contact me at alice@test.com or call 555-432-1234 using key cs_live_12345678901234567890123456789012."
    violations = scan_pii(dirty_text)
    assert "PII_EMAIL_DETECTED" in violations
    assert "PII_PHONE_DETECTED" in violations
    assert "CREDENTIAL_API_KEY_DETECTED" in violations


def test_hallucination_missing_citations(sample_retrieved_docs):
    draft = "You should clear your browser cookies and retry your login."
    violations = check_hallucination_and_entailment(
        draft_response=draft,
        citations=[],
        retrieved_docs=sample_retrieved_docs,
    )
    assert "MISSING_DOC_CITATIONS" in violations


def test_hallucination_invented_doc_id(sample_retrieved_docs):
    draft = "Please see our troubleshooting guide [DOC-FAKE-999] for details."
    violations = check_hallucination_and_entailment(
        draft_response=draft,
        citations=["DOC-FAKE-999"],
        retrieved_docs=sample_retrieved_docs,
    )
    assert any("HALLUCINATED_DOC_ID" in v for v in violations)


def test_hallucination_low_entailment(sample_retrieved_docs):
    draft = "Quantum teleportation enables instantaneous interplanetary data streaming [DOC-AUTH-001]."
    violations = check_hallucination_and_entailment(
        draft_response=draft,
        citations=["DOC-AUTH-001"],
        retrieved_docs=sample_retrieved_docs,
        min_entailment_ratio=0.50,
    )
    assert any("LOW_UNIGRAM_ENTAILMENT" in v for v in violations)


def test_guardrails_passed(sample_retrieved_docs):
    draft = (
        "Confirm whether the account is locked by checking the security page [DOC-AUTH-001]. "
        "You can clear browser cookies and cache to retry [DOC-AUTH-001]."
    )
    status, violations = evaluate_guardrails(
        draft_response=draft,
        citations=["DOC-AUTH-001"],
        retrieved_docs=sample_retrieved_docs,
    )
    assert status == "PASSED"
    assert violations == []


def test_guardrails_tripped_on_leak(sample_retrieved_docs):
    draft = "Please use API key cs_live_12345678901234567890123456789012 per [DOC-AUTH-001]."
    status, violations = evaluate_guardrails(
        draft_response=draft,
        citations=["DOC-AUTH-001"],
        retrieved_docs=sample_retrieved_docs,
    )
    assert status == "TRIPPED"
    assert "CREDENTIAL_API_KEY_DETECTED" in violations

