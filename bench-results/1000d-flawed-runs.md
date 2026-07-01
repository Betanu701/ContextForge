# 1000d flawed run artifacts

These artifacts are preserved only to show that ContextForge could execute the 1000d recall-benchmark workload shape. They should not be cited as meaningful benchmark results.

Why this branch exists:

- The run completed far enough to prove the harness, adapter, judge path, and long-duration execution flow could operate.
- The setup was later judged flawed for benchmark interpretation, so the reported scores, heatmaps, hallucination rates, and latency numbers are not apples-to-apples evidence and should not be used in OSS-facing claims.
- Keeping the artifacts on a separate branch lets us inspect failure patterns and future-memory architecture ideas without mixing these numbers into the release-ready benchmark story.

Included run folders:

- `contextforge-gpt54-wiki-semantic-backend-1000d-sample50-no-daylookup-neutralcat-20260620-0049`: preflight/log-only artifact.
- `contextforge-gpt54-wiki-semantic-backend-1000d-weekly143-sample50-no-daylookup-neutralcat-20260620-1113`: early weekly 1000d attempt.
- `contextforge-gpt54-wiki-semantic-backend-1000d-weekly143-sample50-no-daylookup-neutralcat-csvranges-20260620-1116`: completed weekly 143-checkpoint artifact, retained for debugging and architecture analysis only.

Use the 500d artifacts on the main benchmark branch for external comparisons. Use these 1000d artifacts only for internal diagnosis of where ContextForge struggled and what the future memory architecture needs to address.
