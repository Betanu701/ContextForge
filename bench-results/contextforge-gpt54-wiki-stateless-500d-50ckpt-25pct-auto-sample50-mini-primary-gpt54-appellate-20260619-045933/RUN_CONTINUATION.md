# Run Continuation Note

This directory contains the original ContextForge WikiMemory 500d / 50-checkpoint Recall Bench run.

The run completed checkpoint rows `10d` through `220d`. During evaluation around the next checkpoint, the benchmark stopped because the LLM judge returned near-valid JSON with a malformed wrapper artifact, specifically an extra closing bracket in the score object. The failure was in judge-output parsing, not in ContextForge ingestion or retrieval state.

After the parser was made tolerant of this judge-output shape, the benchmark was resumed with Recall Bench `--resume` using this directory's `progress.jsonl` as the source of cached checkpoints.

Recall Bench resume behavior intentionally writes fresh checkpoint rows to a new run directory. It loaded the cached rows from this directory, catch-up ingested through day `220`, skipped the already completed checkpoints, and continued evaluation from `230d` onward.

For reporting, this directory should be treated as the first segment of one logical run:

- `10d` through `220d`: this original directory
- `230d` onward: the continuation directory

At final reporting time, we should create a combined `progress.jsonl` by taking the original cached checkpoint rows through `220d` and appending the continuation checkpoint rows from `230d` through `500d`, so the published benchmark can be shown as one continuous resumed run.
