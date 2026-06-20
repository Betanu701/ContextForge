"""ContextForge — Give any LLM unlimited memory. One line of code.

Usage::

    import os
    from contextforge import ContextForge

    layer = ContextForge(provider="openai", api_key=os.environ["OPENAI_API_KEY"])
    await layer.ingest("./docs/")
    response = await layer.chat("What was the Q3 revenue?")
"""

from __future__ import annotations

__version__ = "0.1.0"

from .infinite_context import InfiniteContext, InfiniteContextStats
from .layer import ContextForge
from .providers import LLMProvider, get_provider
from .tree import WorkingSet

__all__ = [
    "ContextForge",
    "InfiniteContext",
    "InfiniteContextStats",
    "LLMProvider",
    "WorkingSet",
    "__version__",
    "get_provider",
]
