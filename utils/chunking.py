"""Chunking helpers for knowledge base ingestion.

We intentionally keep this lightweight (no tokenizer dependency). Token counts are
estimated to keep chunks roughly within 500-1000 tokens for MVP ingestion.
"""

from __future__ import annotations

from dataclasses import dataclass


def estimate_tokens(text: str) -> int:
    """Very rough token estimate: ~4 chars per token for English-ish text."""

    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    token_estimate: int


def chunk_markdown(
    text: str,
    *,
    chunk_size_tokens: int = 800,
    chunk_overlap_tokens: int = 120,
) -> list[Chunk]:
    """Split markdown-ish text into overlapping chunks.

    Strategy:
    - Split by blank lines into paragraphs.
    - Accumulate paragraphs into ~chunk_size_tokens using an estimated token count.
    - Add a small overlapping tail between chunks to preserve continuity.
    """

    normalized = (text or "").replace("\r\n", "\n").strip()
    if not normalized:
        return []

    paragraphs = [p.strip() for p in normalized.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []

    current_parts: list[str] = []
    current_tokens = 0
    chunk_index = 0

    def flush() -> None:
        nonlocal chunk_index, current_parts, current_tokens
        if not current_parts:
            return
        joined = "\n\n".join(current_parts).strip()
        chunks.append(
            Chunk(
                index=chunk_index,
                text=joined,
                token_estimate=estimate_tokens(joined),
            )
        )
        chunk_index += 1

        if chunk_overlap_tokens <= 0:
            current_parts = []
            current_tokens = 0
            return

        # Create overlap from the tail of the current chunk.
        tail_chars = chunk_overlap_tokens * 4
        tail = joined[-tail_chars:].strip()
        current_parts = [tail] if tail else []
        current_tokens = estimate_tokens(tail)

    for paragraph in paragraphs:
        paragraph_tokens = estimate_tokens(paragraph)
        if current_parts and current_tokens + paragraph_tokens > chunk_size_tokens:
            flush()

        current_parts.append(paragraph)
        current_tokens += paragraph_tokens

        # If a single paragraph is huge, flush it as its own chunk.
        if current_tokens >= chunk_size_tokens * 1.4:
            flush()

    flush()
    return chunks

