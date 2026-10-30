import re
from src.core.models import DocumentChunk

SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+|\n+")
WORD_REGEX = re.compile(r"\b[a-zA-Z0-9_\-]{3,}\b")


def check_hallucination_and_entailment(
    draft_response: str,
    citations: list[str],
    retrieved_docs: list[DocumentChunk],
    min_entailment_ratio: float = 0.50,
) -> list[str]:
    """
    Validates citation integrity and factual grounding:
    1. At least one citation must be present.
    2. All cited [DOC-ID]s must exist in retrieved_docs.
    3. Lexical unigram entailment ratio between sentences and context must be >= min_entailment_ratio.
    """
    if not draft_response:
        return ["EMPTY_RESPONSE"]

    violations: list[str] = []

    # 1. Citations existence check
    if not citations:
        violations.append("MISSING_DOC_CITATIONS")
        return violations

    # 2. Check citation membership against retrieved docs
    retrieved_doc_ids = {d.doc_id for d in retrieved_docs}
    for cited in citations:
        if cited not in retrieved_doc_ids:
            violations.append(f"HALLUCINATED_DOC_ID: {cited} not in retrieved context")

    # 3. Lexical entailment check
    # Build unigram vocabulary from cited context chunks
    relevant_chunks = [d for d in retrieved_docs if d.doc_id in citations] or retrieved_docs
    context_text = " ".join(d.text for d in relevant_chunks).lower()
    context_unigrams = set(WORD_REGEX.findall(context_text))

    if not context_unigrams:
        violations.append("EMPTY_RETRIEVED_CONTEXT")
        return violations

    sentences = [s.strip() for s in SENTENCE_SPLIT_REGEX.split(draft_response) if s.strip()]
    sentence_scores: list[float] = []

    for sentence in sentences:
        words = [w.lower() for w in WORD_REGEX.findall(sentence)]
        # Skip very short sentences or headings (less than 4 content words)
        if len(words) < 4:
            continue
        overlap_count = sum(1 for w in words if w in context_unigrams)
        ratio = overlap_count / len(words)
        sentence_scores.append(ratio)

    if sentence_scores:
        avg_entailment = sum(sentence_scores) / len(sentence_scores)
        if avg_entailment < min_entailment_ratio:
            violations.append(
                f"LOW_UNIGRAM_ENTAILMENT: ratio={avg_entailment:.2f} < {min_entailment_ratio:.2f}"
            )

    return violations

