# ContextForge 180d Results Table

Combined logical run: original `6d-24d` plus continuation `30d-180d`. Timing comes from completed checkpoint rows in `progress.jsonl`.

## Summary

| Metric | Value |
|---|---:|
| Checkpoints | 30 |
| Question evaluations | 1,615 |
| Weighted score | 5.572/6 (92.9%) |
| Weighted hallucination | 1.5% |
| Total row query time | 1h 36m |
| Weighted per-question query | 3.59s/q |
| Total ingest time | 3m 03s |

## Pertinent Extremes

| Item | Row | Value |
|---|---:|---:|
| Best score | 6d | 6.000/6 (100.0%) |
| Lowest score | 162d | 5.031/6 (83.9%) |
| Highest hallucination | 132d | 5.8% |
| Fastest per-question query | 30d | 2.91s/q |
| Slowest per-question query | 6d | 5.66s/q |

## Checkpoint Detail

| Day | Score | Hallucination | Qs | New/Historical | Row Query | Per-Q Query | Ingest | Segment |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 6d | 6.000 (100.0%) | 0.0% | 1 | 1/0 | 5.7s | 5.66s/q | 18.7s | original |
| 12d | 5.917 (98.6%) | 0.0% | 12 | 11/1 | 40.8s | 3.40s/q | 1.2s | original |
| 18d | 5.880 (98.0%) | 0.0% | 25 | 13/12 | 1m 28s | 3.51s/q | 1.4s | original |
| 24d | 5.900 (98.3%) | 0.0% | 40 | 15/25 | 2m 08s | 3.21s/q | 1.9s | original |
| 30d | 5.981 (99.7%) | 0.0% | 52 | 12/40 | 2m 31s | 2.91s/q | 2.0s | continuation |
| 36d | 5.931 (98.9%) | 0.0% | 58 | 8/50 | 3m 15s | 3.36s/q | 2.3s | continuation |
| 42d | 5.839 (97.3%) | 0.0% | 62 | 12/50 | 3m 22s | 3.26s/q | 2.7s | continuation |
| 48d | 5.804 (96.7%) | 1.8% | 56 | 6/50 | 3m 08s | 3.36s/q | 2.9s | continuation |
| 54d | 5.639 (94.0%) | 3.3% | 61 | 11/50 | 3m 29s | 3.43s/q | 3.3s | continuation |
| 60d | 5.692 (94.9%) | 1.5% | 65 | 15/50 | 3m 45s | 3.46s/q | 3.8s | continuation |
| 66d | 5.672 (94.5%) | 1.7% | 58 | 8/50 | 3m 33s | 3.67s/q | 4.0s | continuation |
| 72d | 5.646 (94.1%) | 3.1% | 65 | 15/50 | 3m 39s | 3.37s/q | 4.4s | continuation |
| 78d | 5.556 (92.6%) | 3.2% | 63 | 13/50 | 3m 35s | 3.42s/q | 4.4s | continuation |
| 84d | 5.724 (95.4%) | 1.7% | 58 | 8/50 | 3m 32s | 3.66s/q | 4.6s | continuation |
| 90d | 5.712 (95.2%) | 0.0% | 52 | 2/50 | 3m 03s | 3.52s/q | 5.1s | continuation |
| 96d | 5.721 (95.4%) | 1.6% | 61 | 11/50 | 3m 25s | 3.36s/q | 5.8s | continuation |
| 102d | 5.683 (94.7%) | 0.0% | 63 | 13/50 | 3m 59s | 3.79s/q | 6.2s | continuation |
| 108d | 5.333 (88.9%) | 0.0% | 63 | 13/50 | 3m 52s | 3.68s/q | 6.2s | continuation |
| 114d | 5.793 (96.6%) | 1.7% | 58 | 8/50 | 3m 25s | 3.54s/q | 6.6s | continuation |
| 120d | 5.586 (93.1%) | 1.7% | 58 | 8/50 | 3m 34s | 3.70s/q | 6.8s | continuation |
| 126d | 5.475 (91.2%) | 0.0% | 59 | 9/50 | 3m 46s | 3.83s/q | 7.2s | continuation |
| 132d | 5.288 (88.1%) | 5.8% | 52 | 2/50 | 3m 18s | 3.81s/q | 7.6s | continuation |
| 138d | 5.224 (87.1%) | 3.4% | 58 | 8/50 | 3m 45s | 3.88s/q | 8.3s | continuation |
| 144d | 5.443 (90.7%) | 1.6% | 61 | 11/50 | 3m 50s | 3.77s/q | 8.4s | continuation |
| 150d | 5.475 (91.3%) | 1.6% | 61 | 11/50 | 3m 57s | 3.88s/q | 8.4s | continuation |
| 156d | 5.232 (87.2%) | 0.0% | 56 | 6/50 | 3m 38s | 3.90s/q | 9.1s | continuation |
| 162d | 5.031 (83.9%) | 0.0% | 64 | 14/50 | 4m 04s | 3.82s/q | 9.4s | continuation |
| 168d | 5.254 (87.6%) | 1.7% | 59 | 9/50 | 3m 48s | 3.87s/q | 9.6s | continuation |
| 174d | 5.288 (88.1%) | 5.8% | 52 | 2/50 | 3m 07s | 3.59s/q | 9.9s | continuation |
| 180d | 5.435 (90.6%) | 1.6% | 62 | 12/50 | 3m 46s | 3.65s/q | 10.2s | continuation |

Notes: `Row Query` is total query time for all evaluated questions in that checkpoint. `Per-Q Query` is `queryMs / questionsEvaluated`. Token diagnostics were not included in the available 180d run artifacts, so this table stays to score, hallucination, question-count, and timing fields present in the benchmark rows.
