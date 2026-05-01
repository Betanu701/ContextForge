"""Local OpenAI-compatible LLM example for ContextForge.

Optional environment variables:
    CONTEXTFORGE_LOCAL_BASE_URL=http://localhost:8080/v1
    CONTEXTFORGE_LOCAL_MODEL=default
"""

from __future__ import annotations

import asyncio
import os

from contextforge import ContextForge


async def main() -> None:
    forge = ContextForge(
        provider="local",
        base_url=os.environ.get("CONTEXTFORGE_LOCAL_BASE_URL", "http://localhost:8080/v1"),
        model=os.environ.get("CONTEXTFORGE_LOCAL_MODEL", "default"),
        db_path="./local_llm.db",
    )

    await forge.ingest_text(
        "ContextForge stores knowledge in a local SQLite-backed tree, "
        "indexes it for fast keyword lookup, and loads relevant branches "
        "into each model request.",
        title="ContextForge Local Overview",
        category="product",
    )

    response = await forge.chat("How does ContextForge work with a local LLM?")
    print(response)

    forge.close()


if __name__ == "__main__":
    asyncio.run(main())