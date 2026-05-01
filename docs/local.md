# Local LLM Setup

ContextForge can run against any local or self-hosted OpenAI-compatible chat completions endpoint. Use the `local` provider when the server exposes `/v1/chat/completions`.

## Install

```bash
pip install contextforge
```

For development from a checkout:

```bash
pip install -e ".[dev]"
```

## Configure ContextForge

```python
from contextforge import ContextForge

forge = ContextForge(
    provider="local",
    base_url="http://localhost:8080/v1",
    model="default",
    db_path="./local_contextforge.db",
)
```

The `model` value is passed to your local server. Some runtimes ignore it, while others require it to match the loaded model name.

## Common Endpoints

| Runtime | Typical base URL | Notes |
|---------|------------------|-------|
| llama-server | `http://localhost:8080/v1` | Start llama.cpp with OpenAI-compatible server mode. |
| vLLM | `http://localhost:8000/v1` | Use the model name served by vLLM. |
| Ollama | `http://localhost:11434/v1` | Use an installed model such as `llama3.1` or `mistral`. |
| LM Studio | `http://localhost:1234/v1` | Start the local server from LM Studio. |
| text-generation-webui | `http://localhost:5000/v1` | Enable the OpenAI-compatible API extension. |

## Minimal Example

```python
import asyncio

from contextforge import ContextForge


async def main() -> None:
    forge = ContextForge(
        provider="local",
        base_url="http://localhost:8080/v1",
        model="default",
        db_path="./local_contextforge.db",
    )

    await forge.ingest_text(
        "ContextForge stores memory locally in SQLite and loads relevant "
        "knowledge into each model request.",
        title="Local Overview",
        category="product",
    )

    print(await forge.chat("Where is ContextForge memory stored?"))
    forge.close()


asyncio.run(main())
```

See [examples/local_llm.py](../examples/local_llm.py) for a runnable script.

## Environment Variable Pattern

For reusable apps, read the endpoint and model from environment variables:

```bash
export CONTEXTFORGE_LOCAL_BASE_URL="http://localhost:8080/v1"
export CONTEXTFORGE_LOCAL_MODEL="default"
```

```python
import os

from contextforge import ContextForge

forge = ContextForge(
    provider="local",
    base_url=os.environ.get("CONTEXTFORGE_LOCAL_BASE_URL", "http://localhost:8080/v1"),
    model=os.environ.get("CONTEXTFORGE_LOCAL_MODEL", "default"),
)
```

No cloud credentials are required for local inference. The only persistent file ContextForge creates by default is the SQLite database path you configure.