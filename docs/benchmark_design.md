# Benchmark Design

## Why 15 Turns

Fifteen turns are long enough to test more than single-turn retrieval. The sequence includes initial retrieval, drill-downs, topic switches, return-to-prior-topic prompts, and final synthesis.

## Why Progressive Complexity

The benchmark starts with direct retrieval and moves toward aggregation, domain reasoning, memory, recall, and synthesis. This progression makes it easier to see where each system succeeds or fails.

## Why LLM-As-Judge

The benchmark responses may be correct in different formats. The LLM judge is instructed to evaluate substance rather than exact presentation, including whether the response addresses the right drug class, state, city, year, provider type, and key data points.

## Why Multi-Cycle Runs

Multi-cycle runs expose variability across repeated executions. The script aggregates cycle-level and per-turn metrics so comparisons are not limited to a single pass through the conversation.

## Conversation Shape

- T01-T03: retrieval
- T04-T06: aggregation
- T07-T09: domain reasoning
- T10-T12: memory and recall
- T13-T15: synthesis