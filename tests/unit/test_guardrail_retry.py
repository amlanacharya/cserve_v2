from types import SimpleNamespace

from src.core.models import DocumentChunk
from src.orchestrator import nodes


def _state(chunks):
    t = SimpleNamespace(subject="s", body="b")
    return {"canonical_ticket": t, "draft_response": "Invent unrelated flamingo trampoline nonsense [DOC-AUTH-001].",
            "citations": ["DOC-AUTH-001"], "retrieved_docs": chunks}


def _chunk():
    return DocumentChunk(
        chunk_id="c1", doc_id="DOC-AUTH-001", title="Auth", heading_path="Auth",
        text="Rotate the api key from the settings page under security.", ordinal=0, similarity=0.9,
    )


def test_retry_off_by_default(monkeypatch):
    monkeypatch.delenv("GUARDRAIL_RETRY", raising=False)
    calls = []
    monkeypatch.setattr(nodes, "generate_response", lambda **k: calls.append(k))
    out = nodes.guardrails_node(_state([_chunk()]))
    assert out["final_disposition"] == "ESCALATED_GUARDRAIL" and not calls


def test_retry_recovers_once(monkeypatch):
    monkeypatch.setenv("GUARDRAIL_RETRY", "1")
    calls = []

    def stub(**k):
        calls.append(k)
        return {"draft_response": "Rotate the api key from the settings page [DOC-AUTH-001].",
                "citations": ["DOC-AUTH-001"]}

    monkeypatch.setattr(nodes, "generate_response", stub)
    out = nodes.guardrails_node(_state([_chunk()]))
    assert out["final_disposition"] == "AUTO_RESOLVED"
    assert len(calls) == 1 and calls[0]["retry_violations"] and calls[0]["retry_unsupported"]


def test_retry_bounded_and_escalates(monkeypatch):
    monkeypatch.setenv("GUARDRAIL_RETRY", "1")
    calls = []

    def stub(**k):
        calls.append(k)
        return {"draft_response": "Still flamingo trampoline nonsense [DOC-AUTH-001].", "citations": ["DOC-AUTH-001"]}

    monkeypatch.setattr(nodes, "generate_response", stub)
    out = nodes.guardrails_node(_state([_chunk()]))
    assert out["final_disposition"] == "ESCALATED_GUARDRAIL" and len(calls) == 1


def test_pii_not_retried(monkeypatch):
    monkeypatch.setenv("GUARDRAIL_RETRY", "1")
    calls = []
    monkeypatch.setattr(nodes, "generate_response", lambda **k: calls.append(k))
    st = _state([_chunk()])
    st["draft_response"] = "Contact bob@example.com to rotate the api key [DOC-AUTH-001]."
    out = nodes.guardrails_node(st)
    assert out["final_disposition"] == "ESCALATED_GUARDRAIL" and not calls


def _strict_stub(text, needs_human):
    def stub(**k):
        assert k.get("strict") is True
        return {"draft_response": text, "citations": ["DOC-AUTH-001"], "needs_human": needs_human}
    return stub


def test_strict_accepts_two_supported_sentences(monkeypatch):
    monkeypatch.setenv("GUARDRAIL_RETRY_STRICT", "1")
    monkeypatch.setattr(nodes, "generate_response", _strict_stub(
        "Rotate the api key from the settings page [DOC-AUTH-001]. The settings page lists security options [DOC-AUTH-001].", False))
    out = nodes.guardrails_node(_state([_chunk()]))
    assert out["final_disposition"] == "AUTO_RESOLVED"


def test_strict_needs_human_escalates(monkeypatch):
    monkeypatch.setenv("GUARDRAIL_RETRY_STRICT", "1")
    monkeypatch.setattr(nodes, "generate_response", _strict_stub(
        "Rotate the api key from the settings page [DOC-AUTH-001]. The settings page lists security [DOC-AUTH-001].", True))
    out = nodes.guardrails_node(_state([_chunk()]))
    assert out["final_disposition"] == "ESCALATED_GUARDRAIL"


def test_strict_rejects_single_sentence_and_non_answers(monkeypatch):
    monkeypatch.setenv("GUARDRAIL_RETRY_STRICT", "1")
    monkeypatch.setattr(nodes, "generate_response", _strict_stub(
        "Rotate the api key from the settings page [DOC-AUTH-001].", False))
    assert nodes.guardrails_node(_state([_chunk()]))["final_disposition"] == "ESCALATED_GUARDRAIL"
    monkeypatch.setattr(nodes, "generate_response", _strict_stub(
        "Rotate the api key from the settings page [DOC-AUTH-001]. The documentation does not cover rotation schedules for the settings page [DOC-AUTH-001].", False))
    assert nodes.guardrails_node(_state([_chunk()]))["final_disposition"] == "ESCALATED_GUARDRAIL"


def test_needs_human_line_stripped(monkeypatch):
    from src.generation import generator
    monkeypatch.setattr(generator, "call_cascade", lambda **k: ("Rotate keys [DOC-AUTH-001].\nNEEDS_HUMAN: no", "stub"))
    r = generator.generate_response("s", "b", [_chunk()], retry_violations=["x"], strict=True)
    assert "NEEDS_HUMAN" not in r["draft_response"] and r["needs_human"] is False
