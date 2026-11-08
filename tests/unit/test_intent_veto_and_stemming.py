from src.classify.classifier import VETO_INTENTS, _apply_intent_veto
from src.core.models import DocumentChunk
from src.guardrails.hallucination import check_hallucination_and_entailment


def test_veto_intents_force_escalation_flag():
    for intent in VETO_INTENTS:
        assert _apply_intent_veto({"inferred_intent": intent, "must_not_auto_respond": False})["must_not_auto_respond"]


def test_other_intents_not_vetoed():
    res = {"inferred_intent": "billing_query", "must_not_auto_respond": False}
    assert _apply_intent_veto(res)["must_not_auto_respond"] is False


def test_data_residency_is_vetoed():
    assert "data_residency" in VETO_INTENTS


def _chunk(text):
    return DocumentChunk(chunk_id="DOC-A-001#x", doc_id="DOC-A-001", title="t", heading_path="h", ordinal=0, text=text)


def test_stemming_matches_inflected_forms():
    ctx = [_chunk("Rotation of keys requires generating a secondary credential before revoking the primary credential.")]
    draft = "Rotate keys by generating secondary credentials, then revoke the primary credential [DOC-A-001]."
    assert check_hallucination_and_entailment(draft, ["DOC-A-001"], ctx) == []
