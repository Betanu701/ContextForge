"""Shared environment configuration for the 15-turn benchmark.

Loads settings from environment variables or from a local .env file in this
directory. Do not commit real Azure endpoints, workspace IDs, or secrets.

Usage:
    from env_config import cfg

    # Access any value:
    cfg.AZURE_ENDPOINT
    cfg.FABRIC_WORKSPACE_ID
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent


def _load_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env parser — no external dependency required."""
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            env[key] = value
    return env


class _Config:
    """Lazily resolved configuration backed by env vars / .env file."""

    def __init__(self) -> None:
        # Determine which .env file to load.
        # Priority: CF_ENV_FILE env var -> .env in this directory
        env_file = os.environ.get("CF_ENV_FILE")
        if env_file:
            self._dotenv = _load_dotenv(Path(env_file))
        elif (_SCRIPT_DIR / ".env").is_file():
            self._dotenv = _load_dotenv(_SCRIPT_DIR / ".env")
        else:
            self._dotenv = {}

    def _get(self, key: str, default: str = "") -> str:
        """Look up key in: real env vars → .env file → default."""
        return os.environ.get(key, self._dotenv.get(key, default))

    def _require(self, key: str) -> str:
        """Like _get but abort if missing."""
        val = self._get(key)
        if not val:
            print(
                f"\033[1;31m[ERROR]\033[0m  Missing required config: {key}\n"
                f"         Set it in your .env file or as an environment variable.\n"
                f"         See benchmarks/15turn/.env.example or config/env_schema.md for the full list.",
                file=sys.stderr,
            )
            sys.exit(1)
        return val

    # ── Azure OpenAI / Cognitive Services ─────────────────────────────────
    @property
    def AZURE_ENDPOINT(self) -> str:
        return self._require("AZURE_ENDPOINT")

    @property
    def DEPLOYMENT_NAME(self) -> str:
        return self._get("DEPLOYMENT_NAME", "gpt-5.4")

    @property
    def API_VERSION(self) -> str:
        return self._get("API_VERSION", "2024-12-01-preview")

    # ── Foundry Agent ─────────────────────────────────────────────────────
    @property
    def FOUNDRY_PROJECT_ENDPOINT(self) -> str:
        return self._get("FOUNDRY_PROJECT_ENDPOINT")

    @property
    def FOUNDRY_AGENT_NAME(self) -> str:
        return self._get("FOUNDRY_AGENT_NAME", "flash-test-001")

    @property
    def FOUNDRY_AGENT_VERSION(self) -> str:
        return self._get("FOUNDRY_AGENT_VERSION", "2")

    # ── Fabric / Power BI ────────────────────────────────────────────────
    @property
    def FABRIC_WORKSPACE_ID(self) -> str:
        return self._get("FABRIC_WORKSPACE_ID")

    @property
    def DATASET_ID(self) -> str:
        return self._get("DATASET_ID")

    @property
    def FABRIC_LAKEHOUSE_ID(self) -> str:
        return self._get("FABRIC_LAKEHOUSE_ID")

    @property
    def FABRIC_SQL_ENDPOINT(self) -> str:
        return self._get("FABRIC_SQL_ENDPOINT")

    @property
    def FABRIC_SQL_ENDPOINT_ID(self) -> str:
        return self._get("FABRIC_SQL_ENDPOINT_ID")

    @property
    def FABRIC_SQL_DATABASE(self) -> str:
        return self._get("FABRIC_SQL_DATABASE", "cms_lakehouse")

    @property
    def FABRIC_WORKSPACE_NAME(self) -> str:
        return self._get("FABRIC_WORKSPACE_NAME")

    @property
    def FABRIC_LAKEHOUSE_NAME(self) -> str:
        return self._get("FABRIC_LAKEHOUSE_NAME", "cms_lakehouse")

    @property
    def FABRIC_CAPACITY(self) -> str:
        return self._get("FABRIC_CAPACITY")

    @property
    def FABRIC_RG(self) -> str:
        return self._get("FABRIC_RG")

    # ── Rosie (Fabric Data Agent) ────────────────────────────────────────
    @property
    def ROSIE_DATAAGENT_ID(self) -> str:
        return self._get("ROSIE_DATAAGENT_ID")

    @property
    def ROSIE_BASE_URL(self) -> str:
        """Build the Rosie OpenAI-compatible URL from workspace + agent IDs."""
        ws = self.FABRIC_WORKSPACE_ID
        da = self.ROSIE_DATAAGENT_ID
        if ws and da:
            return (
                f"https://api.fabric.microsoft.com/v1/workspaces/"
                f"{ws}/dataagents/{da}/aiassistant/openai"
            )
        return self._get("ROSIE_BASE_URL")


cfg = _Config()


def scrub_text(text: str) -> str:
    """Remove tenant-specific Azure identifiers from text for safe storage.

    Replaces endpoint URLs, resource names, workspace/dataset GUIDs, and
    other environment-specific values with generic placeholders.
    """
    import re

    # Build replacements from whatever is loaded in cfg._dotenv + env vars
    replacements: list[tuple[str, str]] = []

    # Full endpoint URLs (most specific first)
    ep = cfg._get("AZURE_ENDPOINT")
    if ep:
        # Strip the resource name from the URL for the placeholder
        replacements.append((ep, "https://<azure-ai-endpoint>.cognitiveservices.azure.com/"))
        replacements.append((ep.rstrip("/"), "https://<azure-ai-endpoint>.cognitiveservices.azure.com"))

    foundry_ep = cfg._get("FOUNDRY_PROJECT_ENDPOINT")
    if foundry_ep:
        replacements.append((foundry_ep, "https://<foundry-endpoint>.services.ai.azure.com/api/projects/<project>"))
        replacements.append((foundry_ep.rstrip("/"), "https://<foundry-endpoint>.services.ai.azure.com/api/projects/<project>"))

    sql_ep = cfg._get("FABRIC_SQL_ENDPOINT")
    if sql_ep:
        replacements.append((sql_ep, "<fabric-sql-endpoint>.datawarehouse.fabric.microsoft.com"))

    # GUIDs
    for key, placeholder in [
        ("FABRIC_WORKSPACE_ID", "<workspace-id>"),
        ("DATASET_ID", "<dataset-id>"),
        ("FABRIC_LAKEHOUSE_ID", "<lakehouse-id>"),
        ("FABRIC_SQL_ENDPOINT_ID", "<sql-endpoint-id>"),
        ("ROSIE_DATAAGENT_ID", "<dataagent-id>"),
        ("AZURE_TENANT_ID", "<tenant-id>"),
        ("AZURE_SUBSCRIPTION_ID", "<subscription-id>"),
    ]:
        val = cfg._get(key)
        if val:
            replacements.append((val, placeholder))

    # Named resources
    cap = cfg._get("FABRIC_CAPACITY")
    if cap:
        replacements.append((cap, "<fabric-capacity>"))

    rg = cfg._get("FABRIC_RG")
    if rg:
        replacements.append((rg, "<resource-group>"))

    ws_name = cfg._get("FABRIC_WORKSPACE_NAME")
    if ws_name:
        replacements.append((ws_name, "<workspace-name>"))

    # Extract resource name from endpoint URL.
    if ep:
        m = re.match(r"https?://([^.]+)\.", ep)
        if m:
            resource_name = m.group(1)
            # Replace in display contexts like "on <name> Foundry"
            replacements.append((f"on {resource_name} Foundry", "on Azure AI Foundry"))
            replacements.append((f"{resource_name} Foundry", "Azure AI Foundry"))
            replacements.append((f"{resource_name} AI Services", "Azure AI Services"))
            # Bare resource name last (most generic — could false-match)
            replacements.append((resource_name, "<azure-resource>"))

    # Apply all replacements (order matters — longer/more specific first)
    for old, new in replacements:
        text = text.replace(old, new)

    return text
