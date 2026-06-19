# Run Continuation Note

This directory contains the continuation segment of the ContextForge WikiMemory 500d / 50-checkpoint Recall Bench run.

The original run completed checkpoint rows `10d` through `220d`. During evaluation around the next checkpoint, the benchmark stopped because the LLM judge returned near-valid JSON with a malformed wrapper artifact, specifically an extra closing bracket in the score object. The failure was in judge-output parsing, not in ContextForge ingestion or retrieval state.

After the parser was made tolerant of this judge-output shape, this continuation was launched with Recall Bench `--resume` pointing at the original run's `progress.jsonl`.

Recall Bench resume behavior intentionally writes fresh checkpoint rows to a new run directory. It loaded the cached rows from the original directory, catch-up ingested through day `220`, skipped the already completed checkpoints, and continued evaluation from `230d` onward in this directory.

For reporting, this directory should be treated as the second segment of one logical run:

- `10d` through `220d`: original run directory
- `230d` onward: this continuation directory

At final reporting time, we should create a combined `progress.jsonl` by taking the original cached checkpoint rows through `220d` and appending this continuation's checkpoint rows from `230d` through `500d`, so the published benchmark can be shown as one continuous resumed run.
