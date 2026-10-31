from typing import Literal
from src.core.models import DocumentChunk
from src.guardrails.hallucination import check_hallucination_and_entailment
from src.guardrails.pii import scan_pii


def evaluate_guardrails(
    draft_response: str | None,
    citations: list[str],
    retrieved_docs: list[DocumentChunk],
) -> tuple[Literal["PASSED", "TRIPPED"], list[str]]:
    """
    Evaluates both PII and citation entailment guardrails.
    Returns ("PASSED", []) if clean, otherwise ("TRIPPED", violations).
    """
    if not draft_response:
        return "TRIPPED", ["EMPTY_DRAFT_RESPONSE"]

    violations: list[str] = []

    # 1. PII Scan
    pii_violations = scan_pii(draft_response)
    violations.extend(pii_violations)

    # 2. Hallucination & Citation Check
    hallucination_violations = check_hallucination_and_entailment(
        draft_response=draft_response,
        citations=citations,
        retrieved_docs=retrieved_docs,
    )
    violations.extend(hallucination_violations)

    status: Literal["PASSED", "TRIPPED"] = "TRIPPED" if violations else "PASSED"
    return status, violations


__all__ = ["evaluate_guardrails", "scan_pii", "check_hallucination_and_entailment"]

