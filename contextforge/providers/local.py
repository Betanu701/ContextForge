"""Local LLM provider — works with any OpenAI-compatible endpoint.

Supports llama-server, vLLM, LM Studio, Ollama, text-generation-webui, etc.
Uses ``httpx`` directly (no SDK dependency).
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional

from .base import LLMProvider


class LocalProvider(LLMProvider):
    """Provider for local / self-hosted OpenAI-compatible APIs.

    No extra SDK required — uses ``httpx`` for HTTP calls.

    Example endpoints:
        - llama-server: http://localhost:8080/v1
        - vLLM: http://localhost:8000/v1
        - Ollama: http://localhost:11434/v1
        - LM Studio: http://localhost:1234/v1
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080/v1",
        model: str = "default",
        api_key: str = "not-needed",
        timeout: float = 120.0,
    ) -> None:
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "httpx is required for LocalProvider. "
                "Install it with: pip install contextforge"
            ) from exc

        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout

    async def chat(self, messages: list[dict], **kwargs) -> str:
        import httpx

        payload = {
            "model": kwargs.pop("model", self._model),
            "messages": messages,
            "stream": False,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        import httpx

        payload = {
            "model": kwargs.pop("model", self._model),
            "messages": messages,
            "stream": True,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
