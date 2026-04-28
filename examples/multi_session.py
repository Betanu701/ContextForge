"""Multi-Session — resume conversations across restarts."""

import asyncio
from contextforge import ContextForge


async def session_1():
    """First session — start a conversation."""
    layer = ContextForge(
        provider="openai",
        api_key="sk-your-key-here",
        db_path="./multi_session.db",
    )

    await layer.ingest_text(
        "Project Alpha launched on March 1st. Initial deployment covered "
        "3 regions: US-East, EU-West, AP-Southeast. Performance metrics "
        "showed 99.8% uptime in the first week.",
        title="Project Alpha Launch",
        category="projects",
    )

    # Start a named session
    layer.new_session(session_id="planning-q4", metadata={"user": "alice"})

    response = await layer.chat("Give me a summary of Project Alpha's launch")
    print(f"Session 1 - Response: {response}\n")

    response = await layer.chat("What regions are covered?")
    print(f"Session 1 - Follow-up: {response}\n")

    # Session persists automatically
    session_id = layer.save_session()
    print(f"Saved session: {session_id}")

    layer.close()
    return session_id


async def session_2(session_id: str):
    """Second session — resume the conversation."""
    layer = ContextForge(
        provider="openai",
        api_key="sk-your-key-here",
        db_path="./multi_session.db",
    )

    # Resume the previous conversation
    found = layer.resume_session(session_id)
    print(f"\nResumed session '{session_id}': {found}")

    # The LLM has full context of the previous conversation
    response = await layer.chat("What were the uptime numbers we discussed?")
    print(f"Session 2 - Response: {response}\n")

    # List all sessions
    print("All sessions:")
    for s in layer.list_sessions():
        print(f"  - {s['id']} (created: {s['created_at']})")

    layer.close()


async def main():
    print("=== Session 1: Starting conversation ===")
    session_id = await session_1()

    print("\n=== Session 2: Resuming conversation ===")
    await session_2(session_id)


if __name__ == "__main__":
    asyncio.run(main())
