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
RAW_DOC_ID_REGEX = re.compile(r"(?<!\[)(DOC-[A-Z0-9\-]+)(?!\])")


def normalize_generated_text(text: str) -> str:
    """Normalizes exotic unicode punctuation and guarantees [DOC-ID] bracket enclosure."""
    if not text:
        return ""
    # Normalize exotic unicode spaces and hyphens
    text = (
        text.replace("\u202f", " ")
        .replace("\u00a0", " ")
        .replace("\u200b", "")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    # Ensure any bare DOC-XYZ-123 is cleanly wrapped in [DOC-XYZ-123]
    text = RAW_DOC_ID_REGEX.sub(r"[\1]", text)
    # Clean up double brackets like [[DOC-ID]] if any
    text = text.replace("[[", "[").replace("]]", "]")
    return text


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

    clean_response = normalize_generated_text(raw_response) if raw_response else None
    citations = extract_citations(clean_response) if clean_response else []

    return {
        "draft_response": clean_response,
        "citations": citations,
        "provider_used": provider_used,
    }
