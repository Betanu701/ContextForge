"""LLM provider abstract base class."""

from __future__ import annotations

import abc
from typing import AsyncGenerator


class LLMProvider(abc.ABC):
    """Abstract interface for LLM backends.

    All providers must implement ``chat`` and ``stream``.
    """

    @abc.abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Send messages and return the complete response text."""

    @abc.abstractmethod
    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        """Send messages and yield response tokens as they arrive."""
        # Must be an async generator; the yield below is never reached
        # but is required for the type checker.
        yield ""  # pragma: no cover
