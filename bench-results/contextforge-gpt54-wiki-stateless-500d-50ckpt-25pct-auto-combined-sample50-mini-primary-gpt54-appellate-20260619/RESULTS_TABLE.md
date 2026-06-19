# ContextForge 500d Results Table

Combined logical run: original `10d-220d` plus continuation `230d-500d`. Timing comes from completed checkpoint rows in `progress.jsonl`. Token usage comes from the ContextForge diagnostics file and reflects answer-model calls, not judge/appellate tokens.

## Summary

| Metric | Value |
|---|---:|
| Checkpoints | 50 |
| Question evaluations | 3,164 |
| Weighted score | 5.209/6 (86.8%) |
| Weighted hallucination | 4.3% |
| Total row query time | 3h 20m |
| Weighted per-question query | 3.80s/q |
| Total ingest time | 21m 00s |
| Answer-model total tokens | 150.36M |
| Answer-model prompt tokens | 150.23M |
| Answer-model completion tokens | 129.1K |
| Avg answer-model tokens/query | 47.6K |
| Avg retrieved tokens/query | 57.7K |
| Avg sources/query | 17.1 |

## Pertinent Extremes

| Item | Row | Value |
|---|---:|---:|
| Best score | 40d | 5.948/6 (99.1%) |
| Lowest score | 390d | 4.548/6 (75.8%) |
| Highest hallucination | 470d | 13.2% |
| Fastest per-question query | 30d | 3.15s/q |
| Slowest per-question query | 460d | 4.49s/q |
| Highest avg tokens/query | 480d | 51.2K |

## Checkpoint Detail

| Day | Score | Hallucination | Qs | New/Historical | Row Query | Per-Q Query | Ingest | Answer Tokens | Avg Tokens/Q | Avg Retrieved/Q | Avg Sources/Q | Segment |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 10d | 5.917 (98.6%) | 0.0% | 12 | 12/0 | 40.1s | 3.34s/q | 2.5s | 474.7K | 39.6K | 47.8K | 24.6 | original |
| 20d | 5.885 (98.1%) | 0.0% | 26 | 14/12 | 1m 27s | 3.35s/q | 2.5s | 1.12M | 43.0K | 52.1K | 21.0 | original |
| 30d | 5.923 (98.7%) | 0.0% | 52 | 26/26 | 2m 44s | 3.15s/q | 3.4s | 2.39M | 46.0K | 55.9K | 21.1 | original |
| 40d | 5.948 (99.1%) | 0.0% | 58 | 8/50 | 3m 08s | 3.24s/q | 4.0s | 2.66M | 45.8K | 55.8K | 19.7 | original |
| 50d | 5.857 (97.6%) | 1.3% | 77 | 27/50 | 4m 15s | 3.32s/q | 4.8s | 3.60M | 46.8K | 57.1K | 20.3 | original |
| 60d | 5.642 (94.0%) | 7.5% | 67 | 17/50 | 3m 41s | 3.30s/q | 5.8s | 3.07M | 45.9K | 55.8K | 19.8 | original |
| 70d | 5.714 (95.2%) | 1.4% | 70 | 20/50 | 3m 55s | 3.35s/q | 6.8s | 3.30M | 47.2K | 57.2K | 18.8 | original |
| 80d | 5.606 (93.4%) | 0.0% | 66 | 16/50 | 3m 37s | 3.29s/q | 7.6s | 3.14M | 47.6K | 57.6K | 19.3 | original |
| 90d | 5.667 (94.4%) | 1.7% | 60 | 10/50 | 3m 52s | 3.86s/q | 8.7s | 2.69M | 44.8K | 54.0K | 18.3 | original |
| 100d | 5.527 (92.1%) | 1.4% | 74 | 24/50 | 4m 14s | 3.43s/q | 9.1s | 3.64M | 49.2K | 59.6K | 19.1 | original |
| 110d | 5.453 (90.9%) | 0.0% | 64 | 14/50 | 3m 53s | 3.65s/q | 10.5s | 3.11M | 48.6K | 58.9K | 18.6 | original |
| 120d | 5.600 (93.3%) | 1.5% | 65 | 15/50 | 3m 58s | 3.67s/q | 11.7s | 3.11M | 47.9K | 58.2K | 18.7 | original |
| 130d | 5.317 (88.6%) | 1.7% | 60 | 10/50 | 3m 32s | 3.54s/q | 12.6s | 2.86M | 47.6K | 57.9K | 18.6 | original |
| 140d | 5.348 (89.1%) | 2.9% | 69 | 19/50 | 4m 29s | 3.90s/q | 13.4s | 3.34M | 48.4K | 58.7K | 18.7 | original |
| 150d | 5.468 (91.1%) | 1.6% | 62 | 12/50 | 3m 57s | 3.83s/q | 14.7s | 2.93M | 47.3K | 57.5K | 17.8 | original |
| 160d | 5.220 (87.0%) | 1.7% | 59 | 9/50 | 3m 45s | 3.82s/q | 15.6s | 2.87M | 48.6K | 59.0K | 18.0 | original |
| 170d | 4.900 (81.7%) | 1.4% | 70 | 20/50 | 4m 24s | 3.77s/q | 16.1s | 3.43M | 49.0K | 59.5K | 18.0 | original |
| 180d | 5.344 (89.1%) | 1.6% | 64 | 14/50 | 4m 03s | 3.79s/q | 16.9s | 2.92M | 45.6K | 55.4K | 17.1 | original |
| 190d | 5.343 (89.0%) | 0.0% | 70 | 20/50 | 4m 18s | 3.68s/q | 18.5s | 3.36M | 47.9K | 58.4K | 16.3 | original |
| 200d | 5.159 (86.0%) | 3.2% | 63 | 13/50 | 3m 52s | 3.68s/q | 19.3s | 2.97M | 47.2K | 57.4K | 16.8 | original |
| 210d | 5.179 (86.3%) | 1.5% | 67 | 17/50 | 4m 01s | 3.59s/q | 20.8s | 3.33M | 49.7K | 60.5K | 17.1 | original |
| 220d | 5.145 (85.8%) | 1.6% | 62 | 12/50 | 3m 58s | 3.83s/q | 20.9s | 2.91M | 46.9K | 56.8K | 17.6 | original |
| 230d | 5.293 (88.2%) | 0.0% | 58 | 8/50 | 3m 43s | 3.84s/q | 22.2s | 2.75M | 47.3K | 57.4K | 16.2 | continuation |
| 240d | 5.329 (88.8%) | 1.4% | 73 | 23/50 | 4m 34s | 3.75s/q | 23.2s | 3.39M | 46.5K | 56.2K | 16.6 | continuation |
| 250d | 5.207 (86.8%) | 5.2% | 58 | 8/50 | 3m 33s | 3.67s/q | 24.2s | 2.78M | 47.9K | 58.3K | 15.4 | continuation |
| 260d | 5.000 (83.3%) | 5.7% | 70 | 20/50 | 4m 23s | 3.76s/q | 26.1s | 3.39M | 48.4K | 58.9K | 16.0 | continuation |
| 270d | 5.419 (90.3%) | 6.5% | 62 | 12/50 | 3m 57s | 3.82s/q | 26.6s | 3.16M | 51.0K | 61.8K | 17.4 | continuation |
| 280d | 4.910 (81.8%) | 6.0% | 67 | 17/50 | 4m 11s | 3.75s/q | 27.2s | 3.13M | 46.7K | 56.4K | 15.2 | continuation |
| 290d | 5.161 (86.0%) | 9.7% | 62 | 12/50 | 4m 17s | 4.14s/q | 29.2s | 2.96M | 47.7K | 58.2K | 16.2 | continuation |
| 300d | 5.339 (89.0%) | 1.7% | 59 | 9/50 | 3m 41s | 3.74s/q | 29.4s | 2.98M | 50.5K | 61.5K | 15.9 | continuation |
| 310d | 5.347 (89.1%) | 1.4% | 72 | 22/50 | 4m 30s | 3.75s/q | 31.2s | 3.50M | 48.6K | 58.8K | 15.4 | continuation |
| 320d | 5.070 (84.5%) | 7.0% | 57 | 7/50 | 3m 35s | 3.78s/q | 32.1s | 2.68M | 47.1K | 57.2K | 14.8 | continuation |
| 330d | 5.000 (83.3%) | 4.1% | 74 | 24/50 | 4m 36s | 3.72s/q | 32.9s | 3.22M | 43.5K | 52.7K | 16.1 | continuation |
| 340d | 4.730 (78.8%) | 4.8% | 63 | 13/50 | 4m 18s | 4.09s/q | 33.5s | 3.09M | 49.0K | 59.6K | 15.3 | continuation |
| 350d | 5.000 (83.3%) | 3.2% | 63 | 13/50 | 4m 26s | 4.22s/q | 34.8s | 3.15M | 49.9K | 60.6K | 17.2 | continuation |
| 360d | 5.113 (85.2%) | 4.8% | 62 | 12/50 | 4m 09s | 4.01s/q | 35.9s | 3.10M | 50.1K | 60.7K | 17.2 | continuation |
| 370d | 5.190 (86.5%) | 4.8% | 63 | 13/50 | 4m 05s | 3.89s/q | 37.4s | 2.97M | 47.1K | 57.0K | 17.0 | continuation |
| 380d | 4.618 (77.0%) | 10.5% | 76 | 26/50 | 5m 01s | 3.96s/q | 38.6s | 3.36M | 44.2K | 53.5K | 15.2 | continuation |
| 390d | 4.548 (75.8%) | 12.9% | 62 | 12/50 | 4m 18s | 4.16s/q | 38.8s | 2.87M | 46.4K | 56.4K | 15.2 | continuation |
| 400d | 4.691 (78.2%) | 7.4% | 68 | 18/50 | 4m 48s | 4.24s/q | 39.8s | 3.13M | 46.0K | 55.8K | 15.7 | continuation |
| 410d | 4.921 (82.0%) | 6.3% | 63 | 13/50 | 4m 14s | 4.03s/q | 40.6s | 2.87M | 47.0K | 57.1K | 15.3 | continuation |
| 420d | 5.273 (87.9%) | 1.5% | 66 | 16/50 | 4m 28s | 4.05s/q | 40.5s | 3.16M | 47.9K | 58.2K | 15.9 | continuation |
| 430d | 5.226 (87.1%) | 4.8% | 62 | 12/50 | 3m 58s | 3.84s/q | 42.2s | 2.89M | 46.7K | 56.5K | 15.6 | continuation |
| 440d | 5.111 (85.2%) | 7.9% | 63 | 13/50 | 4m 10s | 3.97s/q | 44.5s | 2.88M | 45.7K | 55.2K | 16.6 | continuation |
| 450d | 5.071 (84.5%) | 2.9% | 70 | 20/50 | 4m 44s | 4.06s/q | 45.1s | 3.26M | 46.6K | 56.3K | 16.0 | continuation |
| 460d | 4.787 (79.8%) | 11.5% | 61 | 11/50 | 4m 34s | 4.49s/q | 44.2s | 3.01M | 49.4K | 59.7K | 17.2 | continuation |
| 470d | 4.574 (76.2%) | 13.2% | 68 | 18/50 | 4m 47s | 4.21s/q | 47.3s | 3.24M | 47.7K | 57.9K | 15.1 | continuation |
| 480d | 5.048 (84.1%) | 4.8% | 62 | 12/50 | 4m 10s | 4.04s/q | 46.8s | 3.17M | 51.2K | 62.0K | 16.0 | continuation |
| 490d | 4.928 (82.1%) | 13.0% | 69 | 19/50 | 4m 34s | 3.96s/q | 49.7s | 3.27M | 47.4K | 57.0K | 16.5 | continuation |
| 500d | 4.608 (76.8%) | 12.2% | 74 | 24/50 | 5m 05s | 4.12s/q | 50.2s | 3.76M | 50.8K | 61.5K | 15.6 | continuation |

Notes: `Row Query` is total query time for all evaluated questions in that checkpoint. `Per-Q Query` is `queryMs / questionsEvaluated`. `Answer Tokens` are answer-model tokens captured by provider usage in diagnostics; judge and appellate judge tokens are not included. For any checkpoint with extra diagnostics from the interrupted segment, token stats use the latest completed checkpoint-sized slice for that day.
