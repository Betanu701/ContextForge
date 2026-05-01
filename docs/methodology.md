# Methodology

This document describes how the 15-turn benchmark was run and how to interpret the published results. The benchmark is included as artifact code for transparency. It is not a turnkey public benchmark because it depends on private Azure AI Foundry and Microsoft Fabric resources.

## Objective

The benchmark compares how ContextForge and a configured Azure AI Foundry Agent handle the same long-horizon analytical conversation. It focuses on context management behavior across a fixed sequence of prompts rather than broad model quality.

The measured dimensions are:

- Answer quality on a 0-10 LLM-as-judge scale.
- Turn latency.
- Token usage.
- Successful versus errored turns.
- Content-filtered turns.
- Behavior on recall, back-reference, topic-switching, and synthesis prompts.

## Test Subject Scope

The benchmark compares two configured systems:

- **ContextForge:** loads schema and domain hints into its knowledge tree, generates an analytical query, executes the benchmark's DAX ground truth through the Power BI executeQueries API, and synthesizes the answer.
- **Foundry Agent:** uses the configured Azure AI Foundry Agent and Fabric Data Agent tool, preserving its own conversation thread across turns.

The benchmark does not claim to compare every possible ContextForge deployment or every possible Foundry Agent configuration. Results apply to the tested setup, dataset shape, model deployment, tool configuration, and prompt sequence.

## Dataset And Infrastructure

The benchmark used a CMS Medicare Part D analytical dataset exposed through Microsoft Fabric and queried through the Power BI executeQueries API. The fixed DAX queries in `benchmarks/15turn/benchmark_15turn.py` are treated as ground truth for data-bearing turns.

The required infrastructure includes:

- Azure OpenAI or Azure AI Services endpoint for model and judge calls.
- Azure AI Foundry project and Foundry Agent version.
- Microsoft Fabric workspace and dataset.
- Power BI executeQueries access to the dataset.
- Azure authentication through `DefaultAzureCredential` and Azure CLI tokens.

Because these resources are tenant-specific, most OSS readers should treat the benchmark code as a reproducibility record and adaptation starting point, not as a command expected to run successfully after cloning the repository.

## Conversation Design

The benchmark uses a fixed 15-turn conversation. Each system receives the same user turns in the same order.

The turn sequence covers:

- Initial retrieval over drug class, geography, provider type, and year.
- Drill-downs into city, provider, and total-cost detail.
- Topic switches across drug classes.
- Back-references to earlier turns.
- Recall and synthesis turns that do not execute DAX directly.
- Final cross-topic synthesis.

The conversation is intentionally narrow and repeatable. It is designed to stress multi-turn context behavior, not to represent all healthcare analytics workloads.

## Execution Order

Each cycle runs the complete Foundry Agent conversation first, followed by the complete ContextForge conversation. The same 15-turn prompt sequence is used for both systems.

For data-bearing turns, the benchmark stores a DAX query with the turn definition. Those DAX queries are executed through Power BI and used as ground truth for answer synthesis and judging. For recall and synthesis turns, no DAX query is executed; scoring depends on whether the response correctly uses prior conversation context.

The published report includes two comparable cycles. A third attempted cycle was excluded because the Foundry Agent experienced cascading Fabric tool failures while ContextForge changed provider token behavior during the same attempt. Including that cycle would have mixed infrastructure failure and code-change effects into the comparison.

## Controls

The benchmark controls these variables:

- Same user prompt sequence for both systems.
- Same configured model deployment for ContextForge response generation and judge calls.
- Same LLM-as-judge rubric for both systems.
- Same ground-truth DAX for data-bearing turns.
- Same scoring scale and aggregation logic across cycles.

Variables that are not fully controlled include:

- Foundry Agent internals and Fabric Data Agent tool behavior.
- Azure OpenAI content filtering behavior.
- Network and service latency.
- Any model or service-side changes outside the repository.

## Scoring

Responses are evaluated by an LLM judge using the rubric in `benchmarks/15turn/judge_config.md`. The judge scores each response from 0 to 10 based on substance rather than exact formatting.

The judge checks whether the answer addresses the correct:

- Drug class.
- State or city.
- Year.
- Provider type.
- Ranked rows, totals, or key data points.
- Prior turns for recall and synthesis prompts.

Scores are aggregated by turn, by cycle, and across all included cycles. The report also records content-filter flags, infrastructure errors, latency, and token usage.

## Metrics

Quality score is the primary correctness metric. Latency and token usage are efficiency metrics and should be interpreted alongside answer quality rather than as substitutes for it.

Token totals are especially relevant because the systems manage context differently:

- Foundry Agent maintains a single conversation thread, so prompt context can grow across turns.
- ContextForge retrieves and injects relevant context for each turn, so per-turn context can remain more bounded.

Latency includes model calls and tool/API work performed during each benchmark path. It is useful for comparing the tested workflow, but it is not a general service-level latency guarantee.

## Exclusions

Excluded runs or cycles should not be mixed into published aggregate results. A cycle should be excluded when an external failure or code/configuration change makes it incomparable with the included cycles.

The published two-cycle report excludes one attempted third cycle because:

- The Foundry Agent had repeated Fabric Data Agent `tool_user_error` failures from T09 onward.
- ContextForge's provider behavior changed during the same attempted run.
- The combination made the cycle unsuitable for a fair aggregate comparison.

## Limitations

The benchmark has several important limitations:

- It uses one dataset and one domain-specific conversation.
- It compares specific configured systems, not entire product categories.
- The judge is model-based, so scores can be affected by judge behavior.
- Some failures come from external services, content filtering, or tool integrations rather than core context logic.
- The benchmark code cannot be independently rerun without equivalent private infrastructure.

These limitations do not invalidate the published result, but they should constrain how broadly the result is interpreted.

## Reproducibility Artifacts

The repository includes:

- Benchmark runner: `benchmarks/15turn/benchmark_15turn.py`
- Fixed conversation summary: `benchmarks/15turn/conversation.json`
- Judge rubric: `benchmarks/15turn/judge_config.md`
- Environment schema: `benchmarks/15turn/config/env_schema.md`
- Dataset assumptions: `benchmarks/15turn/config/dataset_assumptions.md`
- Published result summary: `results/15turn/processed/benchmark_15turn_combined_2cycles.md`

Generated raw logs and timestamped reports should remain local unless a run is intentionally promoted into `results/15turn/runs/`.