"""Anthropic (Claude) provider."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Optional

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Provider for the Anthropic Messages API.

    Requires the ``anthropic`` package::

        pip install contextforge[anthropic]
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        **client_kwargs: Any,
    ) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "The anthropic package is required for AnthropicProvider. "
                "Install it with: pip install contextforge[anthropic]"
            ) from exc

        self._client = anthropic.AsyncAnthropic(api_key=api_key, **client_kwargs)
        self._model = model
        self._max_tokens = max_tokens

    async def chat(self, messages: list[dict], **kwargs) -> str:
        # Separate system messages from conversation
        system_parts = []
        conversation = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                conversation.append(msg)

        params: dict[str, Any] = {
            "model": kwargs.pop("model", self._model),
            "max_tokens": kwargs.pop("max_tokens", self._max_tokens),
            "messages": conversation,
        }
        if system_parts:
            params["system"] = "\n\n".join(system_parts)
        params.update(kwargs)

        response = await self._client.messages.create(**params)
        return response.content[0].text if response.content else ""

    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        system_parts = []
        conversation = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                conversation.append(msg)

        params: dict[str, Any] = {
            "model": kwargs.pop("model", self._model),
            "max_tokens": kwargs.pop("max_tokens", self._max_tokens),
            "messages": conversation,
        }
        if system_parts:
            params["system"] = "\n\n".join(system_parts)
        params.update(kwargs)

        async with self._client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text
