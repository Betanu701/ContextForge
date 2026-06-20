# ContextForge

ContextForge is a Python SDK for giving LLM applications persistent, searchable context without running a separate vector database or embeddings service. It stores knowledge and session memory in SQLite, builds a lightweight in-memory index, and loads the most relevant context into each model request.

The same API works with OpenAI, Azure OpenAI, Anthropic, and local OpenAI-compatible servers such as llama-server, vLLM, Ollama, and LM Studio.

```python
from contextforge import ContextForge

forge = ContextForge(provider="local", base_url="http://localhost:8080/v1")

await forge.ingest("./company_docs/", category="docs")
response = await forge.chat("What did we decide about the Q3 launch plan?")
print(response)
```

## What ContextForge Provides

- **Hierarchical knowledge storage** backed by SQLite.
- **Proactive context loading** that finds relevant knowledge before each request.
- **Persistent session memory** that can resume across application restarts.
- **Streaming responses** through the same context-loading path as normal chat.
- **Multi-pass analysis** across matching knowledge domains.
- **Provider flexibility** for hosted and local LLMs.

ContextForge is currently alpha software. The public SDK is intentionally lightweight: local memory is SQLite, provider support is pluggable, and generated benchmark outputs are kept separate from source code.

## Installation

```bash
pip install contextforge
pip install contextforge[openai]
pip install contextforge[anthropic]
pip install contextforge[all]
```

For local development from this repository:

```bash
pip install -e ".[all,dev]"
pytest tests/ -v
```

## Quick Start

```python
import asyncio
import os

from contextforge import ContextForge


async def main() -> None:
    forge = ContextForge(
        provider="openai",
        api_key=os.environ["OPENAI_API_KEY"],
        db_path="./memory.db",
    )

    await forge.ingest_text(
        "Our API uses JWT authentication. Access tokens expire after 1 hour. "
        "Refresh tokens are valid for 30 days.",
        title="API Auth",
        category="engineering",
    )

    response = await forge.chat("How long are API tokens valid?")
    print(response)

    forge.close()


asyncio.run(main())
```

## Local LLM Setup

ContextForge's `local` provider talks to any OpenAI-compatible `/v1/chat/completions` endpoint using `httpx`; no vendor SDK is required.

```python
from contextforge import ContextForge

forge = ContextForge(
    provider="local",
    base_url="http://localhost:8080/v1",
    model="default",
)
```

Common local endpoints:

| Runtime | Base URL |
|---------|----------|
| llama-server | `http://localhost:8080/v1` |
| vLLM | `http://localhost:8000/v1` |
| Ollama | `http://localhost:11434/v1` |
| LM Studio | `http://localhost:1234/v1` |
| text-generation-webui | `http://localhost:5000/v1` |

See [docs/local.md](docs/local.md) and [examples/local_llm.py](examples/local_llm.py) for a runnable local setup.

## Azure Setup

Azure OpenAI and Azure AI Foundry model endpoints work through the OpenAI-compatible provider. Configure the endpoint, key, and deployment name with environment variables, then pass the Azure `/openai/v1/` base URL to ContextForge.

```python
import os

from contextforge import ContextForge

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")

forge = ContextForge(
    provider="openai",
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    model=os.environ["AZURE_OPENAI_DEPLOYMENT"],
    base_url=f"{endpoint}/openai/v1/",
)
```

See [docs/azure.md](docs/azure.md) and [examples/azure_openai.py](examples/azure_openai.py) for details.

## Streaming

```python
async for chunk in forge.stream("Draft the board summary"):
    print(chunk, end="")
```

## Multi-Pass Analysis

For cross-domain questions, ContextForge can query matching knowledge domains separately and synthesize the results.

```python
response = await forge.analyze(
    "How do engineering investments correlate with revenue?"
)
```

## Architecture

```text
ContextForge
|-- KnowledgeTree       SQLite hierarchical document store
|-- MemoryIndex         in-memory BM25-style keyword index
|-- ProactiveLoader     query-aware context selection
|-- SessionStore        persisted conversation state
|-- InfiniteContext     context recycling and permanent context helpers
`-- LLM Providers       OpenAI, Anthropic, Azure OpenAI, local endpoints
```

The default workflow is:

1. Ingest documents, text, or source code into the knowledge tree.
2. Rebuild the in-memory index from the stored knowledge.
3. Load relevant context for each user message.
4. Send the assembled system prompt, session history, and user message to the configured LLM.
5. Store the turn in the session database for later recall.

## API Reference

### `ContextForge`

| Method | Description |
|--------|-------------|
| `await chat(message)` | Send a message and receive a complete response. |
| `await stream(message)` | Stream response tokens incrementally. |
| `await analyze(query)` | Run multi-pass analysis across matching knowledge domains. |
| `await set_permanent_context(text)` | Store permanent context for the infinite-context engine. |
| `await ingest(path)` | Ingest a directory of files. |
| `await ingest_text(text, ...)` | Ingest a single text document. |
| `await ingest_code(directory)` | Ingest source code files. |
| `new_session(id)` | Start a new conversation session. |
| `resume_session(id)` | Resume a previous session. |
| `save_session()` | Return the current session ID after persistence. |
| `list_sessions()` | List stored sessions. |
| `close()` | Close database connections. |

### Constructor Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `provider` | `"openai"` | LLM backend: `"openai"`, `"anthropic"`, or `"local"`. |
| `api_key` | `""` | API key for cloud providers; optional for local endpoints. |
| `model` | Provider default | Model or deployment name. |
| `base_url` | `None` | Endpoint URL override; required for many local and Azure-compatible deployments. |
| `knowledge_dir` | `None` | Directory to ingest during initialization. |
| `db_path` | `"./contextforge.db"` | SQLite database path. |
| `max_context_tokens` | `4096` | Token budget for loaded knowledge context. |
| `system_prompt` | Helpful assistant prompt | Base system prompt for every request. |

## Benchmarks

The 15-turn benchmark compares ContextForge with a configured Azure AI Foundry Agent on the same fixed CMS Medicare Part D conversation. It tests retrieval, drill-downs, topic switches, recall, synthesis, latency, token use, and LLM-as-judge quality scores.

Benchmark code lives in [benchmarks/15turn/](benchmarks/15turn/) as reference artifact code: it is the code used to run the published tests, not a general-purpose benchmark that every reader can execute out of the box. Running it requires access to the same Azure AI Foundry project, Fabric workspace, Power BI dataset, model deployment, and CMS Medicare Part D warehouse shape used for the original run.

Curated published results live under [results/15turn/runs/](results/15turn/runs/); generated local logs and timestamped reports should not be committed unless they are promoted into a named run folder.

Current published run:

- [results/15turn/runs/2026-04-07-2cycles/](results/15turn/runs/2026-04-07-2cycles/) - two evaluation cycles against Azure AI Foundry Agent and ContextForge.

## Examples

- [examples/quickstart.py](examples/quickstart.py) - minimal hosted-provider usage.
- [examples/local_llm.py](examples/local_llm.py) - local OpenAI-compatible endpoint usage.
- [examples/azure_openai.py](examples/azure_openai.py) - Azure OpenAI usage.
- [examples/enterprise_qa.py](examples/enterprise_qa.py) - enterprise knowledge base Q&A.
- [examples/coding_assistant.py](examples/coding_assistant.py) - code project with memory.
- [examples/multi_session.py](examples/multi_session.py) - resumed conversations across restarts.

## Works With

| Provider | Package | Status |
|----------|---------|--------|
| OpenAI | `openai` | Supported |
| Azure OpenAI | `openai` | Supported |
| Azure AI Foundry OpenAI-compatible endpoints | `openai` | Supported |
| Anthropic | `anthropic` | Supported |
| llama-server | Built in via `httpx` | Supported |
| vLLM | Built in via `httpx` | Supported |
| Ollama | Built in via `httpx` | Supported |
| LM Studio | Built in via `httpx` | Supported |
| text-generation-webui | Built in via `httpx` | Supported |

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).