# 2026-04-07 Two-Cycle Benchmark Run

This folder records the completed 15-turn benchmark run that is suitable for OSS publication.

The executable code for this run is kept in `benchmarks/15turn/` as reference artifact code. It is useful for reviewing what was run, but it requires private Azure AI Foundry and Microsoft Fabric resources to execute.

## What Ran

- Benchmark: `benchmarks/15turn/benchmark_15turn.py`
- Conversation: 15 fixed turns over CMS Medicare Part D analytical questions
- Systems: ContextForge and Azure AI Foundry Agent
- Cycles included: 2 comparable cycles
- Model reported by the run: GPT-5.4 for both systems and judge
- Data source reported by the run: CMS Medicare Part D in Microsoft Fabric Lakehouse
- Judge: LLM-as-judge on a 0-10 scale with DAX ground-truth verification

## Results

The full report is stored in [../../processed/benchmark_15turn_combined_2cycles.md](../../processed/benchmark_15turn_combined_2cycles.md).

Key aggregate metrics from the published report:

| Metric | Foundry Agent | ContextForge |
|--------|---------------:|-------------:|
| Quality score | 194 / 300 | 225 / 300 |
| Average latency | 60.5s | 7.6s |
| Turn success rate | 27 / 30 | 28 / 30 |
| Content filter hits | 2 / 30 | 2 / 30 |
| Total tokens | 345,112 | 25,666 |
| Total wall clock | 28.3 min | 3.9 min |

## Excluded Work

A failed attempted run is not included. The published report excludes it because the Foundry Agent experienced cascading Fabric infrastructure failures and ContextForge changed provider token behavior during the same attempt, making that work unsuitable for a fair comparison.

The excluded attempt and its reviewed raw log are kept separately in `../excluded-2026-04-07-fabric-failure/` for audit context only. They should not be aggregated into this published run.