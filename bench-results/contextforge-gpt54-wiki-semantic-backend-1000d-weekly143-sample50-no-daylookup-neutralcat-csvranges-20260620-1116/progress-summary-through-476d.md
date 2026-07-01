# ContextForge 1000d Weekly Benchmark - Partial Progress

As of the latest official progress file, the corrected weekly 1000d ContextForge run has completed 68 of 143 checkpoints, through the 476d range. This represents 4,136 evaluated questions from completed checkpoints. The adapter logs are slightly ahead of the official progress file, but these numbers are based only on persisted checkpoint rows in progress.jsonl.

Current weighted aggregate score is 5.590/6 with a 6.17% hallucination rate. Recent performance is stronger than the full partial average: the last 5 completed checkpoints average 5.808/6 with 4.40% hallucination, and the last 10 average 5.713/6 with 5.49% hallucination.

The latest completed checkpoint is 476d with 64 evaluated questions, scoring 5.766/6 and 4.69% hallucination. The strongest completed checkpoint so far is 371d at 5.953/6. The weakest completed checkpoint remains 154d at 5.094/6, which matches the earlier observed dip around the 147d-154d segment.

Weighted category scores across completed checkpoints:

| Category | Score | Questions |
| --- | ---: | ---: |
| factual-recall | 5.764 | 1,274 |
| temporal-reasoning | 3.830 | 112 |
| decision-tracking | 5.576 | 884 |
| contradiction-resolution | 5.357 | 350 |
| cross-reference | 5.518 | 249 |
| recency-bias-resistance | 5.958 | 214 |
| synthesis | 5.562 | 299 |
| negative-recall | 5.615 | 754 |

Difficulty-weighted scores:

| Difficulty | Score | Questions |
| --- | ---: | ---: |
| easy | 5.750 | 2,423 |
| medium | 5.339 | 1,586 |
| hard | 5.693 | 127 |

Generated artifacts:

- Partial heatmap: heatmap-partial-through-476d.png
- Partial result JSON: partial-result-from-progress.json
