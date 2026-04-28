"""LLM provider factory and public imports."""

from __future__ import annotations

from typing import Optional

from .base import LLMProvider


def get_provider(
    name: str,
    *,
    api_key: str = "",
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """Create an LLM provider by name.

    Args:
        name: One of ``"openai"``, ``"anthropic"``, ``"local"``.
        api_key: API key (required for cloud providers).
        model: Model name override.
        base_url: Endpoint URL override (required for ``"local"``).
        **kwargs: Extra arguments passed to the provider constructor.

    Returns:
        An LLMProvider instance.
    """
    name = name.lower().strip()

    if name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            base_url=base_url,
            **kwargs,
        )
    elif name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
            **kwargs,
        )
    elif name == "local":
        from .local import LocalProvider

        return LocalProvider(
            base_url=base_url or "http://localhost:8080/v1",
            model=model or "default",
            api_key=api_key or "not-needed",
            **kwargs,
        )
    else:
        raise ValueError(
            f"Unknown provider: {name!r}. "
            f"Supported: 'openai', 'anthropic', 'local'"
        )


__all__ = ["LLMProvider", "get_provider"]
