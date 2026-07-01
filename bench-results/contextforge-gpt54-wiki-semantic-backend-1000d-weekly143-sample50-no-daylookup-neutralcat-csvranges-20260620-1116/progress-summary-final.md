# ContextForge 1000d Weekly Benchmark - Final Progress

The corrected weekly 1000d ContextForge run completed all 143 of 143 checkpoints, from 7d through 1000d. The official result metadata reports 8,803 total evaluations, 1,817 unique Q&A pairs, and 666 appellate judge invocations. Total wall time was 29h 21m 46s.

Weighted across completed checkpoint rows, the final aggregate score is 5.595/6 with a 6.09% hallucination rate. The final 1000d checkpoint itself scored 5.339/6 with 9.68% hallucination across 62 evaluated questions.

The strongest checkpoint was 371d at 5.953/6; the weakest was 819d at 5.033/6. Lowest hallucination was 7d at 0.00%; highest hallucination was 966d at 14.52%. The late tail from 966d through 994d is the main visible dip, driven by lower temporal-reasoning and negative-recall scores, before a partial recovery at 1000d.

Window summary:

| Window | Ranges | Checkpoints | Questions | Score | Hallucination |
| --- | --- | ---: | ---: | ---: | ---: |
| first 20 | 7d-140d | 20 | 1,118 | 5.490/6 | 6.89% |
| mid 20 | 441d-574d | 20 | 1,270 | 5.660/6 | 6.46% |
| pre-tail 20 | 728d-861d | 20 | 1,234 | 5.674/6 | 4.78% |
| last 20 | 868d-1000d | 20 | 1,237 | 5.505/6 | 6.55% |
| last 10 | 938d-1000d | 10 | 618 | 5.343/6 | 8.90% |
| last 5 | 973d-1000d | 5 | 310 | 5.165/6 | 11.61% |

Weighted category scores:

| Category | Score | Questions |
| --- | ---: | ---: |
| factual-recall | 5.745/6 | 2,680 |
| temporal-reasoning | 3.772/6 | 202 |
| decision-tracking | 5.569/6 | 2,009 |
| contradiction-resolution | 5.609/6 | 778 |
| cross-reference | 5.532/6 | 600 |
| recency-bias-resistance | 5.851/6 | 389 |
| synthesis | 5.454/6 | 672 |
| negative-recall | 5.625/6 | 1,473 |

Difficulty-weighted scores:

| Difficulty | Score | Questions |
| --- | ---: | ---: |
| easy | 5.744/6 | 5,312 |
| medium | 5.375/6 | 3,248 |
| hard | 5.296/6 | 243 |

Generated artifacts:

- Final progress report: progress-summary-final.md
- Final Recall Bench result: result.json
- Progress-derived final result JSON: final-result-from-progress.json
- Built-in Recall Bench heatmap: heatmap.png
- Final full-width heatmap: heatmap-final-full-width.png
