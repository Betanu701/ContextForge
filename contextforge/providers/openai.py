"""OpenAI / Azure OpenAI provider."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Optional

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI and Azure OpenAI APIs.

    Requires the ``openai`` package::

        pip install contextforge[openai]
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        **client_kwargs: Any,
    ) -> None:
        try:
            import openai
        except ImportError as exc:
            raise ImportError(
                "The openai package is required for OpenAIProvider. "
                "Install it with: pip install contextforge[openai]"
            ) from exc

        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        kwargs.update(client_kwargs)

        self._client = openai.AsyncOpenAI(**kwargs)
        self._model = model

    async def chat(self, messages: list[dict], **kwargs) -> str:
        # GPT-5+ models require max_completion_tokens instead of max_tokens
        if "max_tokens" in kwargs and "max_completion_tokens" not in kwargs:
            kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
        response = await self._client.chat.completions.create(
            model=kwargs.pop("model", self._model),
            messages=messages,  # type: ignore[arg-type]
            stream=False,
            **kwargs,
        )
        self._last_usage = response.usage
        return response.choices[0].message.content or ""

    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        if "max_tokens" in kwargs and "max_completion_tokens" not in kwargs:
            kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
        response = await self._client.chat.completions.create(
            model=kwargs.pop("model", self._model),
            messages=messages,  # type: ignore[arg-type]
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
