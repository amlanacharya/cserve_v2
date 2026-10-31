import re
from src.core.models import DocumentChunk

SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?])\s+|\n+")
WORD_REGEX = re.compile(r"\b[a-zA-Z0-9_\-]{3,}\b")
DOC_ID_TOKEN = re.compile(r"^doc-[a-z0-9\-]+$")
STOP_WORDS = frozenset(
    "the and for are but not you your all any can had her was one our out has have "
    "his how its may new now see two way who did get let put say she too use with "
    "that this from they were been being what when which about would there their "
    "will than then them these those into over such only some also more most very "
    "just like should could does done each both where while your".split()
)


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
    relevant_chunks = [d for d in retrieved_docs if d.doc_id in citations]
    context_text = " ".join(d.text for d in relevant_chunks).lower()
    context_unigrams = {w for w in WORD_REGEX.findall(context_text) if w not in STOP_WORDS}

    if not context_unigrams:
        violations.append("EMPTY_RETRIEVED_CONTEXT")
        return violations

    sentences = [s.strip() for s in SENTENCE_SPLIT_REGEX.split(draft_response) if s.strip()]
    worst: float | None = None

    for sentence in sentences:
        words = [w.lower() for w in WORD_REGEX.findall(sentence)]
        words = [w for w in words if w not in STOP_WORDS and not DOC_ID_TOKEN.match(w)]
        if not words:
            continue
        ratio = sum(1 for w in words if w in context_unigrams) / len(words)
        if worst is None or ratio < worst:
            worst = ratio

    # Any single ungrounded sentence trips the guard.
    if worst is not None and worst < min_entailment_ratio:
        violations.append(
            f"LOW_UNIGRAM_ENTAILMENT: ratio={worst:.2f} < {min_entailment_ratio:.2f}"
        )

    return violations

