# 15-Turn Conversational Benchmark

This folder contains the code used to run the published 15-turn benchmark for ContextForge. It is included for transparency, auditability, and adaptation, but it is not a turnkey public benchmark: running it requires access to the same Azure AI Foundry project, Fabric workspace, Power BI dataset, model deployment, and CMS Medicare Part D warehouse shape used by the original test.

The benchmark evaluates a fixed 15-turn conversation across two systems: ContextForge and Foundry Agent. Each system receives the same user turns in the same order. A separate LLM judge scores each response using the rubric extracted in `judge_config.md`.

## What This Folder Is

- Reference code used for the published benchmark run.
- A reproducibility record for the prompts, DAX ground truth, judge rubric, and result-generation flow.
- A starting point for teams that want to adapt the benchmark to their own Fabric dataset or warehouse.

## What This Folder Is Not

- A benchmark that can be run by any OSS reader without private Azure and Fabric resources.
- A packaged sample dataset or public CMS warehouse.
- A generic benchmark harness independent of the original infrastructure.

## Benchmark Design

The benchmark is a multi-cycle evaluation. For each cycle, Foundry Agent runs the full T01-T15 conversation first, then ContextForge runs the full T01-T15 conversation. The script aggregates scores, latency, token usage, content-filter flags, and per-turn results across cycles.

The conversation uses:

- Back-references to earlier turns
- Topic switching across drug classes
- Progressive drill-downs from broad retrieval to city/provider/cost detail
- Aggregation queries backed by DAX ground truth
- Recall and synthesis turns without direct DAX execution
- Structured hints for evaluation
- An LLM judge scoring rubric

## Turn Groups

- T01-T03: retrieval over drug class, geography, provider type, and year
- T04-T06: aggregation and comparison queries, including city/provider and cost totals
- T07-T09: domain reasoning with a topic switch to statins and provider filtering
- T10-T12: memory and recall, including returning to quinolones and summarizing prior classes
- T13-T15: synthesis across additional drug classes and cross-turn comparison

## DAX Usage

The script stores a ground-truth DAX query for turns that require direct data access. Those DAX queries are executed through the Power BI executeQueries API against the configured Fabric workspace and dataset. Recall and synthesis turns may have no DAX query and instead test conversation memory.

## SQL Generation

ContextForge uses the CMS schema and domain hints loaded into its knowledge tree to generate SQL-like analytical queries. The benchmark then executes the turn's ground-truth DAX query and uses the returned rows for synthesis and judging.

## LLM Judge Scoring

The judge evaluates substance rather than exact formatting. It checks whether each response addresses the correct drug class, state, city, year, provider type, and key data points. See `judge_config.md` for the full prompt and scoring rubric.

## Run

Most OSS readers will not be able to run this command successfully because the underlying Fabric warehouse and Foundry Agent configuration are environment-specific. The command is documented so the original execution path is visible and so authorized maintainers can rerun it.

The Python package dependencies for this artifact are listed in `requirements.txt` in this folder. They are intentionally not kept as the repository-level requirements because the public ContextForge package dependencies are declared in `pyproject.toml`.

From the repository root:

```bash
python3 -m pip install -r benchmarks/15turn/requirements.txt
python3 benchmarks/15turn/benchmark_15turn.py
```

Generated outputs are written under `results/15turn/`.

The script writes timestamped raw logs and processed JSON/Markdown reports. Treat those as local generated artifacts until you intentionally promote a completed run into a named folder under `results/15turn/runs/`.

## Published Results

Only completed benchmark runs should be committed as published results. Placeholder files, empty summaries, and failed or incomparable cycles should stay out of the curated result folders.

The current published run is `results/15turn/runs/2026-04-07-2cycles/`, which summarizes the two comparable cycles from April 7, 2026. A third attempted cycle is explicitly excluded in that report because infrastructure failures and a concurrent provider fix made it incomparable.

## Required Environment Variables

The script reads configuration through `env_config.py`. These values identify private or tenant-specific resources and should not be committed. Required variable names are:

- AZURE_ENDPOINT
- DEPLOYMENT_NAME
- API_VERSION
- FOUNDRY_PROJECT_ENDPOINT
- FOUNDRY_AGENT_NAME
- FOUNDRY_AGENT_VERSION
- FABRIC_WORKSPACE_ID
- DATASET_ID

See `.env.example` for a local template and `config/env_schema.md` for descriptions.