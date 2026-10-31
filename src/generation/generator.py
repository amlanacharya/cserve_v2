import re
from typing import Any
from src.core.config import get_settings
from src.core.models import DocumentChunk
from src.generation.cascade import call_cascade
from src.generation.prompts import (
    GENERATION_SYSTEM_PROMPT,
    format_generation_prompt,
)

DOC_CITATION_REGEX = re.compile(r"\[(DOC-[A-Z0-9\-]+)\]")


def extract_citations(text: str) -> list[str]:
    """Extracts unique [DOC-ID] bracket citations preserving appearance order."""
    if not text:
        return []
    matches = DOC_CITATION_REGEX.findall(text)
    # Deduplicate while preserving order
    return list(dict.fromkeys(matches))


def generate_response(
    subject: str | None,
    body: str,
    retrieved_docs: list[DocumentChunk],
) -> dict[str, Any]:
    """
    Compiles XML-sandboxed prompt with top retrieved context chunks,
    invokes the inference cascade, and extracts doc citations.
    """
    settings = get_settings()
    top_docs = retrieved_docs[: settings.top_k_passages]

    doc_dicts = [{"doc_id": d.doc_id, "text": d.text} for d in top_docs]
    user_prompt = format_generation_prompt(subject, body, doc_dicts)

    raw_response, provider_used = call_cascade(
        system_prompt=GENERATION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=settings.generation_temperature,
        task_type="generation",
    )

    citations = extract_citations(raw_response)

    return {
        "draft_response": raw_response if raw_response else None,
        "citations": citations,
        "provider_used": provider_used,
    }

