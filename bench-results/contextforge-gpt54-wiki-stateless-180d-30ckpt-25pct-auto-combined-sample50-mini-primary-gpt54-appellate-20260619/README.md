# ContextForge 180d / 30-Checkpoint Combined Run

This folder presents the original run and continuation as one logical benchmark run.

- Original segment: `contextforge-gpt54-wiki-stateless-180d-30ckpt-25pct-auto-sample50-mini-primary-gpt54-appellate-20260619-093348`
- Continuation segment: `contextforge-gpt54-wiki-stateless-180d-30ckpt-25pct-auto-continuation-sample50-mini-primary-gpt54-appellate-20260619-094659`
- Combined checkpoints: 30
- Total question evaluations: 1615
- Weighted score: 5.572/6.0 (92.9%)
- Weighted hallucination: 1.5%
- Total row query time: 5790.3s
- Total ingest time across benchmark rows: 182.5s

## Continuation Note

The original segment completed `6d` through `24d`. The benchmark was then continued in the continuation folder, which produced fresh completed checkpoint rows from `30d` through `180d`. This combined folder keeps those two physical runs visible while presenting the 30 completed checkpoints as one logical 180d benchmark.

## Files

- `progress.jsonl`: clean combined checkpoint stream, header plus 30 checkpoint rows.
- `questions-original.jsonl`: original segment per-question log, preserved as emitted.
- `questions-continuation.jsonl`: continuation segment per-question log, preserved as emitted.
- `failures-continuation.jsonl`: continuation segment judge/appellate failure log, preserved as emitted.
- `result-continuation-report.json`: completed Recall Bench result report emitted by the continuation run.
- `heatmap-1.png`: score heatmap by category and checkpoint.
- `RESULTS_TABLE.md`: chart/table view of checkpoint scores, hallucinations, and timings.
