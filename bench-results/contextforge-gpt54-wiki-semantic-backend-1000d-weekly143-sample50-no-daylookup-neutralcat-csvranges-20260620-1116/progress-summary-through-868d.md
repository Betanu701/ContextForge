# ContextForge 1000d Weekly Benchmark - Partial Progress

As of the latest official progress file, the corrected weekly 1000d ContextForge run has completed 124 of 143 checkpoints (86.7%), through the 868d range. This represents 7,630 evaluated questions from completed checkpoint rows. Adapter logs can run ahead of this file, so these numbers use only persisted `type == "checkpoint"` rows in `progress.jsonl`.

The current weighted aggregate score is 5.609/6 with a 6.03% hallucination rate. Recent windows remain useful for trend watching: the last 10 checkpoints average 5.531/6 with 6.77% hallucination, while the last 20 average 5.656/6 with 5.02% hallucination.

The latest completed checkpoint is 868d with 64 evaluated questions, scoring 5.469/6 and 7.81% hallucination. The strongest completed checkpoint so far is 371d at 5.953/6; the weakest is 819d at 5.033/6. The lowest hallucination checkpoint is 7d at 0.00%; the highest is 154d at 14.06%.

Recent-window summary:

| Window | Ranges | Checkpoints | Questions | Score | Hallucination |
| --- | --- | ---: | ---: | ---: | ---: |
| first 20 | 7d-140d | 20 | 1,118 | 5.490/6 | 6.89% |
| middle 20 | 371d-504d | 20 | 1,278 | 5.656/6 | 6.34% |
| last 20 | 735d-868d | 20 | 1,236 | 5.656/6 | 5.02% |
| last 10 | 805d-868d | 10 | 620 | 5.531/6 | 6.77% |
| last 5 | 840d-868d | 5 | 311 | 5.595/6 | 6.11% |

Weighted category scores across completed checkpoints:

| Category | Score | Questions |
| --- | ---: | ---: |
| factual-recall | 5.746/6 | 2,339 |
| temporal-reasoning | 3.855/6 | 173 |
| decision-tracking | 5.573/6 | 1,738 |
| contradiction-resolution | 5.602/6 | 686 |
| cross-reference | 5.523/6 | 512 |
| recency-bias-resistance | 5.902/6 | 347 |
| synthesis | 5.489/6 | 569 |
| negative-recall | 5.656/6 | 1,266 |

Difficulty-weighted scores:

| Difficulty | Score | Questions |
| --- | ---: | ---: |
| easy | 5.744/6 | 4,594 |
| medium | 5.391/6 | 2,834 |
| hard | 5.594/6 | 202 |

Generated artifacts:

- Partial progress report: progress-summary-through-868d.md
- Partial heatmap source JSON: partial-result-through-868d.json
- Stable heatmap source JSON: partial-result-from-progress.json
- Partial heatmap: heatmap-partial-through-868d.png
