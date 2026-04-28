# Azure Integration

ContextForge works with Azure OpenAI and Azure AI Foundry through the existing OpenAI-compatible provider. The open-source SDK keeps deployment simple: use SQLite for local ContextForge memory, configure your Azure model endpoint with environment variables, and keep cloud credentials outside source control.

## Install

```bash
pip install contextforge[openai]
```

For development from a checkout:

```bash
pip install -e ".[openai,dev]"
```

## Azure OpenAI

Set these environment variables before running your app:

```bash
export AZURE_OPENAI_ENDPOINT="https://<resource-name>.openai.azure.com/"
export AZURE_OPENAI_API_KEY="<api-key>"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o-mini"
```

Then configure ContextForge with the OpenAI-compatible Azure endpoint:

```python
import os

from contextforge import ContextForge

endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")

forge = ContextForge(
    provider="openai",
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    base_url=f"{endpoint}/openai/v1/",
)
```

The `model` value should be your Azure OpenAI deployment name, not necessarily the underlying model family name.

## Azure AI Foundry

Foundry serverless and model endpoints can also expose OpenAI-compatible chat completions. Use the same provider and set `base_url` to the Foundry endpoint when it supports the OpenAI-compatible API:

```bash
export FOUNDRY_OPENAI_ENDPOINT="https://<endpoint-name>.<region>.models.ai.azure.com/"
export FOUNDRY_OPENAI_API_KEY="<api-key>"
export FOUNDRY_MODEL="gpt-4o-mini"
```

```python
import os

from contextforge import ContextForge

forge = ContextForge(
    provider="openai",
    api_key=os.environ["FOUNDRY_OPENAI_API_KEY"],
    model=os.environ.get("FOUNDRY_MODEL", "gpt-4o-mini"),
    base_url=os.environ["FOUNDRY_OPENAI_ENDPOINT"],
)
```

Endpoint formats vary by Foundry deployment type, so confirm the target URI in the Foundry portal for your deployed model.

## Secrets

Do not commit API keys, connection strings, or generated `.env` files. Prefer one of these patterns:

- Local development: shell environment variables or a local `.env` file ignored by Git.
- CI/CD: repository or organization secrets.
- Azure-hosted workloads: managed identity plus an application-level token flow.
- Production secret storage: Azure Key Vault.

The open-source SDK does not require a cloud database or deployment stack. ContextForge stores its knowledge tree and sessions in SQLite by default.

## Minimal Example

See [examples/azure_openai.py](../examples/azure_openai.py) for a small runnable example that ingests knowledge locally and answers through Azure OpenAI.

## What Is Not Included

The public SDK intentionally does not include enterprise deployment automation for Fabric, PostgreSQL, Key Vault provisioning, nightly jobs, or connector validation. Those patterns are useful for larger internal deployments, but they are broader than the SDK surface and should live separately until they are ready as supported integrations.
