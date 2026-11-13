"""Deterministic customer-message envelope (PRD FR-03 citation footer, FR-05 machine disclaimer).

Applied after the guardrails pass, in Python, never by the model. The validated draft stays
untouched in `final_response`; the envelope is a separate `customer_message`.
"""
from src.core.models import DocumentChunk

MACHINE_DISCLAIMER = (
    "[Automated Support Assistant] This message was drafted automatically by "
    "CloudServe's AI Support Assistant using our official documentation."
)


def format_customer_message(draft: str, citations: list[str], docs: list[DocumentChunk]) -> str:
    titles = {d.doc_id: d.title for d in docs}
    refs = [f"[{c}: {titles[c]}]" if c in titles else f"[{c}]" for c in citations]
    footer = ("\n\nReference: " + ", ".join(refs)) if refs else ""
    return f"{MACHINE_DISCLAIMER}\n\n{draft.strip()}{footer}"
