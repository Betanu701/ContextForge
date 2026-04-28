"""Azure OpenAI example for ContextForge.

Required environment variables:
    AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com/
    AZURE_OPENAI_API_KEY=<api-key>
    AZURE_OPENAI_DEPLOYMENT=<deployment-name>
"""

from __future__ import annotations

import asyncio
import os

from contextforge import ContextForge


def azure_openai_base_url(endpoint: str) -> str:
    """Return the OpenAI-compatible Azure endpoint URL."""
    return f"{endpoint.rstrip('/')}/openai/v1/"


async def main() -> None:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_key = os.environ.get("AZURE_OPENAI_API_KEY") or os.environ["AZURE_OPENAI_KEY"]
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    forge = ContextForge(
        provider="openai",
        api_key=api_key,
        model=deployment,
        base_url=azure_openai_base_url(endpoint),
        db_path="./azure_openai.db",
    )

    await forge.ingest_text(
        "ContextForge stores knowledge in a local SQLite-backed tree, "
        "indexes it for fast keyword lookup, and loads the most relevant "
        "branches into each model request.",
        title="ContextForge Overview",
        category="product",
    )

    response = await forge.chat("How does ContextForge decide what context to send?")
    print(response)

    forge.close()


if __name__ == "__main__":
    asyncio.run(main())
