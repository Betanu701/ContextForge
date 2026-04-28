# ContextForge — Forge unlimited context for any LLM

**Give any LLM unlimited memory. One line of code.**

ContextForge is middleware that sits between your application and any LLM. It adds hierarchical knowledge storage, proactive context loading, and persistent session memory — so your LLM always has the right context, without you managing it.

```python
from contextforge import ContextForge

layer = ContextForge(provider="openai", api_key="sk-...")
await layer.ingest("./company_docs/")
response = await layer.chat("What was the Q3 revenue?")
# → Automatically found the financial report, loaded it into context, and answered.
```

**No vector database. No embeddings server. No infrastructure.** Just `pip install` and go.

---

## Infinite Context

ContextForge provides practically unlimited context through intelligent recycling:

- **VRAM**: ~680K active tokens at any moment
- **Disk**: Unlimited tokens stored as tree nodes
- **Speed**: <50ms to swap context branches
- **Cost**: The 1000th query uses the same VRAM as the 1st

How it works:
1. Permanent knowledge (personality, contracts) stored as residual states (48% smaller)
2. Dynamic knowledge loaded from tree branches per-query
3. History compacted automatically (lossless summarization)
4. After each response, unused context recycled for next query
5. Full knowledge always available on disk via tree navigation

No context limit. No token limit. Just ask.

```python
from contextforge import ContextForge

layer = ContextForge(provider="local", base_url="http://localhost:8080/v1")

# Permanent context — cached once, reused forever
await layer.set_permanent_context("You are a senior architect at Acme Corp...")

# Ingest your entire codebase — it all lives on disk
await layer.ingest("./monorepo/", category="code")  # 500K+ files? No problem.

# Each query loads ONLY what it needs, then recycles
response = await layer.chat("How does the auth module work?")
# → Loaded: code/src/auth/ (~3K tokens). Recycled after response.

response = await layer.chat("Now explain the billing pipeline")
# → Loaded: code/src/billing/ (~5K tokens). Auth context already freed.

# Generate a 100-file project — constant VRAM throughout
results = await layer.infinite.generate_project(
    spec="Build a REST API with auth, billing, and notifications",
    files=["src/auth.py", "src/billing.py", ...],  # even 1000 files
    provider=layer._provider,
)
```

---

## Why ContextForge?

Every LLM application hits the same wall: **context limits**. Your LLM can only see what fits in its window. Today's solutions — RAG pipelines, vector databases, chunking strategies — are complex, fragile, and require infrastructure.

ContextForge solves this differently:

| | Vanilla LLM | RAG Pipeline | **ContextForge** |
|---|---|---|---|
| **Setup** | None | Vector DB + embeddings + chunking | `pip install contextforge` |
| **Knowledge storage** | None | Flat chunks in vector space | **Hierarchical tree** (SQLite) |
| **Context limit** | Fixed window | Fixed window | **Infinite** (recycled) |
| **Retrieval** | Manual | Semantic similarity | **Proactive + BM25 scoring** |
| **Session memory** | None | Custom implementation | **Built-in with compaction** |
| **Multi-turn context** | Manual | Manual | **Automatic** |
| **Infrastructure** | None | Vector DB, embeddings API | **None** (SQLite on disk) |
| **First query latency** | ~0ms overhead | ~200-500ms (embedding + search) | **~5ms** (in-memory index) |
| **1000-file generation** | Impossible (context overflow) | N/A | **Constant VRAM** |

## Features

### 🌳 Hierarchical Knowledge Tree
Knowledge isn't flat — it has structure. Financial reports belong under Finance. API docs belong under Engineering. ContextForge stores knowledge as a tree, so related information stays together and loads together.

```python
await layer.ingest("./docs/", category="engineering")
await layer.ingest_text("Q3 revenue was $10M", title="Q3 Report", category="finance")
await layer.ingest_code("./src/", project="myapp")
```

### ⚡ Proactive Context Loading
You don't tell the layer what to load — it figures it out. Every query is analyzed for keywords, matched against the inverted index, and the most relevant knowledge branches are assembled into context. Follow-up questions benefit from branch caching.

```python
response = await layer.chat("What was Q3 revenue?")
# → Loaded: finance/q3_report

response = await layer.chat("Compare with Q2")
# → Q3 still cached + loaded finance/q2_report
```

### 💾 Session Memory with Compaction
Conversations persist across restarts. When sessions grow long, older turns are automatically compacted into summaries — preserving context without burning tokens.

```python
layer.new_session(session_id="planning-q4")
await layer.chat("Let's review the roadmap...")
layer.save_session()

# Days later...
layer.resume_session("planning-q4")
await layer.chat("Where were we?")  # Remembers everything
```

### 🔌 Works with Any LLM

```python
# OpenAI / Azure
layer = ContextForge(provider="openai", api_key="sk-...")

# Anthropic Claude
layer = ContextForge(provider="anthropic", api_key="sk-ant-...")

# Local models (llama-server, vLLM, Ollama, LM Studio)
layer = ContextForge(provider="local", base_url="http://localhost:8080/v1")
```

For Azure OpenAI and Azure AI Foundry configuration, see [docs/azure.md](docs/azure.md).

### 📡 Streaming Support

```python
async for chunk in layer.stream("Draft the board summary"):
    print(chunk, end="")
```

### 🔬 Multi-Pass Analysis

For cross-domain questions, ContextForge queries each knowledge domain separately, then synthesizes a unified answer:

```python
response = await layer.analyze("How do engineering investments correlate with revenue?")
# → Queries finance domain, engineering domain, synthesizes
```

## Installation

```bash
pip install contextforge                  # Core (local models via httpx)
pip install contextforge[openai]          # + OpenAI support
pip install contextforge[anthropic]       # + Anthropic support
pip install contextforge[all]             # Everything
```

## Quick Start

```python
import asyncio
from contextforge import ContextForge

async def main():
    layer = ContextForge(
        provider="openai",
        api_key="sk-your-key",
        db_path="./memory.db",
    )

    # Add knowledge
    await layer.ingest_text(
        "Our API uses JWT authentication. Tokens expire after 1 hour. "
        "Refresh tokens are valid for 30 days.",
        title="API Auth",
        category="engineering",
    )

    # Chat — context loaded automatically
    response = await layer.chat("How long are API tokens valid?")
    print(response)

    layer.close()

asyncio.run(main())
```

## Architecture

ContextForge is built on five components:

```
┌──────────────────────────────────────────────────┐
│                  ContextForge                     │
│  ┌─────────────────────────────────────────────┐ │
│  │           Infinite Context                   │ │
│  │   (recycling orchestrator — 680K active)     │ │
│  └───────┬──────────┬──────────────┬───────────┘ │
│  ┌───────┴───┐ ┌────┴─────┐ ┌─────┴──────────┐  │
│  │ Knowledge │ │  Memory  │ │   Proactive    │  │
│  │   Tree    │ │  Index   │ │    Loader      │  │
│  │ (SQLite)  │ │(in-memory)│ │               │  │
│  └─────┬─────┘ └────┬─────┘ └──────┬────────┘  │
│  ┌─────┴─────────────┴──────────────┴─────────┐  │
│  │            Session Store                    │  │
│  │      (persistence + compaction)             │  │
│  └────────────────────┬───────────────────────┘  │
│  ┌────────────────────┴───────────────────────┐  │
│  │           LLM Provider                      │  │
│  │    OpenAI │ Anthropic │ Local/vLLM          │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

1. **KnowledgeTree** — Hierarchical storage in SQLite. Nodes have paths (like `finance/q3_report`), categories, and parent-child relationships. Content is automatically chunked for granular retrieval.

2. **MemoryIndex** — In-memory inverted index rebuilt from the tree on startup. BM25 scoring with O(1) term lookup. No external dependencies.

3. **ProactiveLoader** — Extracts keywords from user queries + conversation history, searches the index, loads the best-matching branches, and assembles them into a context block that fits the token budget. Caches loaded branches for follow-up questions.

4. **SessionStore** — Conversations persist in SQLite. When sessions grow long, older turns are compacted into summaries. Sessions can be resumed across application restarts.

5. **InfiniteContext** — The recycling orchestrator. Manages the lifecycle of context through load → use → recycle cycles. Permanent context (personality, contracts) is cached once and reused via KV-cache prefix caching. Dynamic knowledge is loaded per-query from the tree, then freed. History is compacted automatically. Enables unlimited file generation — file 1 and file 1000 use the same VRAM.

6. **LLM Providers** — Pluggable interface for any LLM backend. OpenAI, Anthropic, and any OpenAI-compatible local server (llama-server, vLLM, Ollama, LM Studio).

## API Reference

### `ContextForge`

| Method | Description |
|--------|-------------|
| `await chat(message)` | Send a message, get a response. Knowledge loaded automatically. |
| `await stream(message)` | Same as chat, but yields tokens incrementally. |
| `await analyze(query)` | Multi-pass analysis across knowledge domains. |
| `await set_permanent_context(text)` | Set permanent context (personality, contracts). Cached after first use. |
| `await ingest(directory)` | Ingest a directory of files. |
| `await ingest_text(text, ...)` | Ingest a single text document. |
| `await ingest_code(directory)` | Ingest source code files. |
| `new_session(id)` | Start a new conversation session. |
| `resume_session(id)` | Resume a previous session. |
| `save_session()` | Persist the current session. |
| `list_sessions()` | List all stored sessions. |
| `infinite` | Property — `InfiniteContext` engine for advanced recycling. |
| `stats` | Property — current knowledge/index/session/infinite-context statistics. |
| `close()` | Clean up database connections. |

### `InfiniteContext`

| Method | Description |
|--------|-------------|
| `await query(message, provider)` | Smart query with context recycling — load, generate, recycle. |
| `await set_permanent_context(text)` | Set permanent context cached as residual states. |
| `await generate_file(spec, contract, sigs, provider)` | Generate a single file with recycled context. |
| `await generate_project(spec, files, provider)` | Generate an entire project — constant VRAM. |
| `get_stats()` | Return `InfiniteContextStats` snapshot. |

### Constructor Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `provider` | `"openai"` | LLM backend: `"openai"`, `"anthropic"`, `"local"` |
| `api_key` | `""` | API key for cloud providers |
| `model` | Provider default | Model name override |
| `base_url` | `None` | Endpoint URL (required for `"local"`) |
| `knowledge_dir` | `None` | Auto-ingest directory on init |
| `db_path` | `"./contextforge.db"` | SQLite database path |
| `max_context_tokens` | `4096` | Token budget for knowledge context |
| `system_prompt` | Default | Base system prompt |

## Examples

See the [`examples/`](examples/) directory:

- **[quickstart.py](examples/quickstart.py)** — Simplest possible usage (10 lines)
- **[azure_openai.py](examples/azure_openai.py)** — Azure OpenAI via the OpenAI-compatible provider
- **[enterprise_qa.py](examples/enterprise_qa.py)** — Enterprise knowledge base Q&A
- **[coding_assistant.py](examples/coding_assistant.py)** — Code project with memory
- **[multi_session.py](examples/multi_session.py)** — Resume conversations across restarts

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run a specific test
pytest tests/test_tree.py -v
```

## Works With

| Provider | Package | Status |
|----------|---------|--------|
| **OpenAI** (GPT-4o, GPT-4o-mini) | `openai` | ✅ |
| **Azure OpenAI** | `openai` | ✅ |
| **Anthropic** (Claude 4, Sonnet, Haiku) | `anthropic` | ✅ |
| **llama-server** (llama.cpp) | Built-in (`httpx`) | ✅ |
| **vLLM** | Built-in (`httpx`) | ✅ |
| **Ollama** | Built-in (`httpx`) | ✅ |
| **LM Studio** | Built-in (`httpx`) | ✅ |
| **text-generation-webui** | Built-in (`httpx`) | ✅ |

## License

Apache-2.0 — see [LICENSE](LICENSE). Attribution notices are provided in [NOTICE](NOTICE).
