# (c) 2026 Marc Alier i Forment (Universitat Politecnica de Catalunya)
# https://wasabi.essi.upc.edu/ludo - https://lamb-project.org
# BSC Agents Course - Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 - reuse must credit the author,
# no commercial use, derivatives under the same license.

"""Plain chunking utilities from the Week 2 simple-dynamic-rag tool."""

import re


def chunk_by_chars(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    """Sliding window of `size` characters, stepping by size-overlap."""
    step = max(1, size - overlap)
    chunks = []
    i = 0
    while i < len(text):
        piece = text[i:i + size].strip()
        if piece:
            chunks.append(piece)
        i += step
    return chunks


def chunk_by_sections(markdown: str, level: int = 2) -> list[str]:
    """Split a markdown document at headings of `level`."""
    heading = re.compile(rf"^#{{{level}}}\s", flags=re.MULTILINE)
    starts = [m.start() for m in heading.finditer(markdown)]
    if not starts:
        return [markdown.strip()] if markdown.strip() else []
    cuts = [0] + starts + [len(markdown)]
    chunks = []
    for a, b in zip(cuts, cuts[1:]):
        piece = markdown[a:b].strip()
        if piece:
            chunks.append(piece)
    return chunks
