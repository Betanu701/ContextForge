# ContextForge 500d / 50-Checkpoint Combined Run

This folder presents the original run and continuation as one logical benchmark run.

- Original segment: `contextforge-gpt54-wiki-stateless-500d-50ckpt-25pct-auto-sample50-mini-primary-gpt54-appellate-20260619-045933`
- Continuation segment: `contextforge-gpt54-wiki-stateless-500d-50ckpt-25pct-auto-continuation-230d-500d-sample50-mini-primary-gpt54-appellate-20260619-062752`
- Combined checkpoints: 50
- Total question evaluations: 3164
- Weighted score: 5.209/6.0 (86.8%)
- Weighted hallucination: 4.3%
- Total row query time: 12028.1s
- Total ingest time across benchmark rows: 1260.4s

## Aggregate Charts

- [HEATMAP_AGGREGATE_500D.md](HEATMAP_AGGREGATE_500D.md): weighted category aggregate from the 500d heatmap, raw+extra captured scored rows, and ContextForge vs OpenClaw side-by-side category comparison.
- [heatmap-aggregate-500d-side-by-side.svg](heatmap-aggregate-500d-side-by-side.svg): chart image for the aggregate report.

## Continuation Note

The original segment completed `10d` through `220d`. It stopped while entering the next checkpoint because the LLM judge returned malformed near-JSON. The issue was in judge-output parsing, not in ContextForge state or retrieval. The judge parser was hardened, and the benchmark was resumed in the continuation folder with Recall Bench `--resume` so cached checkpoints were skipped and fresh scoring continued from `230d` through `500d`.

## Files

- `progress.jsonl`: clean combined checkpoint stream, header plus 50 checkpoint rows.
- `questions-original.jsonl`: original segment per-question log, preserved as emitted.
- `questions-continuation.jsonl`: continuation segment per-question log, preserved as emitted.
- `failures-original.jsonl`: original segment judge/appellate failure log, preserved as emitted.
- `failures-continuation.jsonl`: continuation segment judge/appellate failure log, preserved as emitted.
- `result-continuation-report.json`: completed Recall Bench result report emitted by the continuation run.
- `HEATMAP_AGGREGATE_500D.md`: category-level aggregate chart report, including the 39 extra scored rows captured in the per-question logs.
- `heatmap-aggregate-500d-side-by-side.svg`: visual chart for the aggregate report.

`progress.jsonl` is the authoritative combined row artifact. The per-question logs are kept per segment to avoid hiding that the original folder may contain partial question events after its last completed checkpoint.
