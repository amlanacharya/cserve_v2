import json
import re
from pathlib import Path
from typing import Any
from src.core.models import DocumentChunk


# Spec 6.2: sections under ~40 tokens merge into the preceding sibling.
MIN_SECTION_TOKENS = 40
TOKENS_PER_WORD = 1.3


def slugify(text: str) -> str:
    """Produce deterministic URL/anchor slugs from heading strings."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


def split_large_section(text: str, max_words: int = 256, overlap_words: int = 30) -> list[str]:
    """
    Splits sections exceeding max_words at paragraph boundaries with overlap_words overlap.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]

    paragraphs = text.split("\n\n")
    sub_chunks: list[str] = []
    current_paragraphs: list[str] = []
    current_word_count = 0

    for para in paragraphs:
        para_words = para.split()
        if not para_words:
            continue
        if current_word_count + len(para_words) > max_words and current_paragraphs:
            sub_chunks.append("\n\n".join(current_paragraphs))
            # Keep overlap words from the end of current paragraphs
            overlap_text = " ".join(" ".join(current_paragraphs).split()[-overlap_words:])
            current_paragraphs = [overlap_text, para]
            current_word_count = len(overlap_text.split()) + len(para_words)
        else:
            current_paragraphs.append(para)
            current_word_count += len(para_words)

    if current_paragraphs:
        sub_chunks.append("\n\n".join(current_paragraphs))

    return sub_chunks if sub_chunks else [text]


def chunk_article(doc_dict: dict[str, Any]) -> list[DocumentChunk]:
    """
    Splits a single Markdown article into semantic DocumentChunks:
    - Splits on H2 (##) and H3 (###) headers.
    - Preamble text before the first header is prepended to the first header section.
    - Merges any section under ~40 tokens into their preceding sibling.
    - Splits sections exceeding 256 words at paragraph boundaries with 30-word overlap.
    - Prefixes text with heading hierarchy (Title > Heading > Text).
    """
    doc_id = doc_dict["doc_id"]
    title = doc_dict["title"]
    content = doc_dict.get("content", "")

    lines = content.split("\n")
    # Each section: (heading_trail, level, text); trail is "H2" or "H2 > H3".
    sections: list[tuple[str, int, str]] = []
    current: tuple[str, int] | None = None
    preamble: list[str] = []
    curr_lines: list[str] = []
    h2 = ""

    for line in lines:
        if line.startswith("## ") or line.startswith("### "):
            if current is None:
                preamble = curr_lines
            else:
                sections.append((current[0], current[1], "\n".join(curr_lines).strip()))
            level = 3 if line.startswith("### ") else 2
            heading = line.lstrip("#").strip()
            if level == 2:
                h2 = heading
                trail = heading
            else:
                trail = f"{h2} > {heading}" if h2 else heading
            current = (trail, level)
            curr_lines = []
        else:
            curr_lines.append(line)

    if current is not None:
        sections.append((current[0], current[1], "\n".join(curr_lines).strip()))
    elif curr_lines:
        sections.append(("Overview", 2, "\n".join(curr_lines).strip()))

    # Prepend preamble to first section if present
    if preamble and sections:
        first_h, first_l, first_t = sections[0]
        sections[0] = (first_h, first_l, ("\n".join(preamble).strip() + "\n\n" + first_t).strip())

    # Merge any section under 40 words into its preceding sibling
    merged: list[tuple[str, int, str]] = []
    for h, lvl, t in sections:
        if merged and len(t.split()) * TOKENS_PER_WORD < MIN_SECTION_TOKENS:
            prev_h, prev_l, prev_t = merged[-1]
            label = h.split(" > ")[-1]
            merged[-1] = (prev_h, prev_l, prev_t + f"\n\n{'#' * lvl} {label}\n" + t)
        else:
            merged.append((h, lvl, t))
    sections = merged

    # Now build DocumentChunks, splitting any section > 256 words if necessary
    chunks: list[DocumentChunk] = []
    ordinal = 0

    for h, _lvl, t in sections:
        sub_texts = split_large_section(t, max_words=256, overlap_words=30)
        for sub_idx, sub_t in enumerate(sub_texts):
            sub_suffix = f"-part{sub_idx+1}" if len(sub_texts) > 1 else ""
            chunk_slug = f"{slugify(h.split(' > ')[-1])}{sub_suffix}"
            chunk_id = f"{doc_id}#{chunk_slug}"
            heading_path = f"{title} > {h}"
            full_text = f"{title} > {h}\n\n{sub_t}"

            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    title=title,
                    heading_path=heading_path,
                    text=full_text,
                    ordinal=ordinal,
                    similarity=None,
                )
            )
            ordinal += 1

    return chunks


def chunk_documentation(docs_path: str | Path) -> list[DocumentChunk]:
    """
    Loads all documentation articles from JSON file and chunks them.
    Asserts chunk count falls within 70-90 chunks for the standard corpus.
    """
    path = Path(docs_path)
    if not path.exists():
        raise FileNotFoundError(f"Documentation file not found: {docs_path}")

    with open(path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    all_chunks: list[DocumentChunk] = []
    for doc in docs:
        all_chunks.extend(chunk_article(doc))

    if not 70 <= len(all_chunks) <= 90:
        raise ValueError(
            f"Chunk count {len(all_chunks)} outside required 70-90 bounds (spec 6.2)"
        )
    return all_chunks
