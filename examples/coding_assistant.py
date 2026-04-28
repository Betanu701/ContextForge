"""Coding Assistant — ingest a project and ask about it."""

import asyncio
from contextforge import ContextForge


async def main():
    layer = ContextForge(
        provider="local",
        base_url="http://localhost:8080/v1",  # llama-server, vLLM, etc.
        db_path="./coding_assistant.db",
        max_context_tokens=8192,
        system_prompt=(
            "You are a senior software engineer. Answer questions about "
            "the codebase using the provided source code context. "
            "Be specific, cite file paths, and suggest improvements."
        ),
    )

    # Ingest a project's source code
    # count = await layer.ingest_code("./my-project/src/", project="myapp")
    # print(f"Ingested {count} source files")

    # For demo, add some inline code knowledge
    await layer.ingest_text(
        """
# auth.py
class AuthService:
    def __init__(self, db, jwt_secret):
        self.db = db
        self.jwt_secret = jwt_secret

    async def login(self, email, password):
        user = await self.db.get_user_by_email(email)
        if not user or not verify_password(password, user.hash):
            raise AuthError("Invalid credentials")
        return create_jwt(user.id, self.jwt_secret)

    async def verify_token(self, token):
        payload = decode_jwt(token, self.jwt_secret)
        return await self.db.get_user(payload["user_id"])
        """,
        title="Authentication Service",
        category="myapp",
    )

    await layer.ingest_text(
        """
# models.py
@dataclass
class User:
    id: int
    email: str
    name: str
    role: str  # 'admin', 'user', 'viewer'
    created_at: datetime

@dataclass
class Project:
    id: int
    name: str
    owner_id: int
    settings: dict
        """,
        title="Data Models",
        category="myapp",
    )

    # Ask about the code
    response = await layer.chat("How does authentication work in this project?")
    print(f"Auth explanation:\n{response}\n")

    response = await layer.chat("What user roles are supported?")
    print(f"Roles:\n{response}\n")

    # Streaming for longer responses
    print("Security review (streaming):")
    async for chunk in layer.stream(
        "Do a security review of the auth service. Any vulnerabilities?"
    ):
        print(chunk, end="", flush=True)
    print()

    layer.close()


if __name__ == "__main__":
    asyncio.run(main())
