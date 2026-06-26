"""Quickstart — simplest possible ContextForge usage."""

import asyncio
import os

from contextforge import ContextForge


async def main():
    # Initialize with OpenAI (or any provider)
    layer = ContextForge(
        provider="openai",
        api_key=os.environ["OPENAI_API_KEY"],
        db_path="./quickstart.db",
    )

    # Ingest some knowledge
    await layer.ingest_text(
        "ContextForge is an SDK that gives any LLM unlimited memory. "
        "It uses a hierarchical knowledge tree stored in SQLite, "
        "an in-memory inverted index for O(1) lookup, and proactive "
        "context loading to automatically find relevant knowledge.",
        title="About ContextForge",
        category="product",
    )

    # Chat loads knowledge automatically and preserves normal session history.
    response = await layer.chat("What is ContextForge?")
    print(response)

    # Follow-up — the previous user/assistant turns are replayed like a normal chatbot.
    response = await layer.chat("How does the lookup work?")
    print(response)

    layer.close()


if __name__ == "__main__":
    asyncio.run(main())
