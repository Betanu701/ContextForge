"""Utility functions for token estimation and keyword extraction."""

from __future__ import annotations

import math
import re
from collections import Counter


# Approximate tokens per character for English text
_CHARS_PER_TOKEN = 4.0

# Common stop words to exclude from keyword extraction
_STOP_WORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "about", "up", "what",
    "which", "who", "whom", "this", "that", "these", "those", "am", "it",
    "its", "i", "me", "my", "we", "our", "you", "your", "he", "him",
    "his", "she", "her", "they", "them", "their",
}

_WORD_RE = re.compile(r"[a-zA-Z0-9_]+")


def estimate_tokens(text: str) -> int:
    """Estimate token count for a string (rough, model-agnostic)."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / _CHARS_PER_TOKEN))


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate total tokens across a list of chat messages."""
    total = 0
    for msg in messages:
        # ~4 tokens overhead per message for role/formatting
        total += 4
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
    return total


def extract_keywords(text: str, top_k: int = 10) -> list[str]:
    """Extract the most significant keywords from text.

    Returns lowercase keywords sorted by frequency, excluding stop words.
    """
    words = _WORD_RE.findall(text.lower())
    filtered = [w for w in words if w not in _STOP_WORDS and len(w) > 2]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(top_k)]


def chunk_text(text: str, max_tokens: int = 512, overlap: int = 64) -> list[str]:
    """Split text into overlapping chunks of approximately max_tokens each."""
    if not text:
        return []

    max_chars = int(max_tokens * _CHARS_PER_TOKEN)
    overlap_chars = int(overlap * _CHARS_PER_TOKEN)
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]

        # Try to break at a sentence or paragraph boundary
        if end < len(text):
            for sep in ("\n\n", "\n", ". ", "! ", "? ", " "):
                last = chunk.rfind(sep)
                if last > max_chars // 2:
                    chunk = chunk[: last + len(sep)]
                    break

        chunks.append(chunk.strip())
        start += len(chunk) - overlap_chars
        if start <= (len(chunks) - 1) * (max_chars - overlap_chars):
            # Prevent infinite loop on very small chunks
            start = (len(chunks)) * (max_chars - overlap_chars)

    return [c for c in chunks if c]
