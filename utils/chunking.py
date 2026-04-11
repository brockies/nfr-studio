"""Chunking helpers for knowledge base ingestion.

We use LangChain text splitters for more robust chunking (demo/client friendly).
When `tiktoken` is available, we do true token-aware chunking; otherwise we fall
back to a character-based approximation (still using LangChain).
"""

from __future__ import annotations

from dataclasses import dataclass


def estimate_tokens(text: str) -> int:
    """Fallback rough token estimate: ~4 chars per token for English-ish text."""

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
    """Split markdown-ish text into overlapping chunks (LangChain-backed)."""

    normalized = (text or "").replace("\r\n", "\n").strip()
    if not normalized:
        return []

    from langchain.text_splitter import RecursiveCharacterTextSplitter

    # Prefer token-aware chunking when possible.
    token_counter = estimate_tokens
    try:
        import tiktoken  # type: ignore

        encoding = tiktoken.get_encoding("cl100k_base")

        def token_counter(value: str) -> int:  # type: ignore[no-redef]
            return len(encoding.encode(value or ""))

        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=chunk_size_tokens,
            chunk_overlap=chunk_overlap_tokens,
            encoding_name="cl100k_base",
            separators=["\n\n", "\n", " ", ""],
        )
    except Exception:
        # Still use LangChain, but approximate tokens as characters.
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size_tokens * 4,
            chunk_overlap=chunk_overlap_tokens * 4,
            separators=["\n\n", "\n", " ", ""],
            length_function=len,
        )

    pieces = [piece.strip() for piece in splitter.split_text(normalized) if piece.strip()]
    return [
        Chunk(index=index, text=piece, token_estimate=token_counter(piece))
        for index, piece in enumerate(pieces)
    ]
