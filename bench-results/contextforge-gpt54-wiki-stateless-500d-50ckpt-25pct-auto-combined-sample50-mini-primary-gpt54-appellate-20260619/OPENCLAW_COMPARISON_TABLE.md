# ContextForge vs OpenClaw 500d Comparison

Same-row comparison using the available OpenClaw 500 artifact at `/tmp/recall/bench-results/openclaw/ea-500d-vector/progress.jsonl`. OpenClaw has 41 matching checkpoint rows in this artifact. ContextForge token usage is answer-model usage from diagnostics; the OpenClaw artifact does not include comparable token diagnostics.

## Aggregate on Matching Rows

| Metric | ContextForge | OpenClaw | Delta / Ratio |
|---|---:|---:|---:|
| Matching checkpoint rows | 41 | 41 | - |
| Row wins / losses / ties | 25/16/0 | - | - |
| Weighted score | 5.106/6 | 4.999/6 | +0.107 |
| Average row score delta | - | - | +0.112 |
| Median row score delta | - | - | +0.081 |
| Weighted hallucination | 4.8% | 17.8% | -13.0pp |
| Total row query time | 2h 53m | 10h 31m | 3.64x faster |
| Weighted per-question query | 3.88s/q | 14.14s/q | 3.64x faster |
| Total ingest time | 20m 14s | 7h 33m | 22.41x faster |
| Avg ingest per row | 29.6s | 11m 04s | 22.41x faster |
| Answer-model total tokens | 127.92M | n/a | OpenClaw token diagnostics unavailable |
| Avg answer tokens/query | 47.8K | n/a | OpenClaw token diagnostics unavailable |
| Avg retrieved tokens/query | 58.0K | n/a | OpenClaw token diagnostics unavailable |
| Avg sources/query | 16.6 | n/a | OpenClaw source diagnostics unavailable |

## Pertinent Rows

| Item | Row | ContextForge | OpenClaw | Delta |
|---|---:|---:|---:|---:|
| Biggest score win | 300d | 5.339/6 | 4.559/6 | +0.780 |
| Biggest score loss | 470d | 4.574/6 | 5.103/6 | -0.529 |
| Biggest hallucination advantage | 300d | 1.7% | 27.1% | -25.4pp |

## Row Detail

| Day | CF Score | OC Score | Score Delta | CF Hall | OC Hall | Hall Delta | CF Per-Q | OC Per-Q | Speedup | CF Ingest | OC Ingest | CF Tokens/Q | CF Retrieved/Q |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100d | 5.527 | 5.149 | +0.378 | 1.4% | 13.5% | -12.2pp | 3.43s/q | 10.33s/q | 3.01x | 9.1s | 2m 02s | 49.2K | 59.6K |
| 110d | 5.453 | 4.844 | +0.609 | 0.0% | 17.2% | -17.2pp | 3.65s/q | 10.25s/q | 2.81x | 10.5s | 2m 23s | 48.6K | 58.9K |
| 120d | 5.600 | 5.077 | +0.523 | 1.5% | 16.9% | -15.4pp | 3.67s/q | 11.31s/q | 3.08x | 11.7s | 2m 44s | 47.9K | 58.2K |
| 130d | 5.317 | 4.933 | +0.383 | 1.7% | 18.3% | -16.7pp | 3.54s/q | 12.15s/q | 3.43x | 12.6s | 2m 55s | 47.6K | 57.9K |
| 140d | 5.348 | 5.203 | +0.145 | 2.9% | 17.4% | -14.5pp | 3.90s/q | 12.72s/q | 3.27x | 13.4s | 3m 46s | 48.4K | 58.7K |
| 150d | 5.468 | 4.710 | +0.758 | 1.6% | 22.6% | -21.0pp | 3.83s/q | 11.51s/q | 3.01x | 14.7s | 4m 25s | 47.3K | 57.5K |
| 160d | 5.220 | 5.033 | +0.187 | 1.7% | 18.3% | -16.6pp | 3.82s/q | 11.88s/q | 3.11x | 15.6s | 4m 52s | 48.6K | 59.0K |
| 170d | 4.900 | 5.100 | -0.200 | 1.4% | 15.7% | -14.3pp | 3.77s/q | 12.73s/q | 3.38x | 16.1s | 5m 17s | 49.0K | 59.5K |
| 180d | 5.344 | 5.109 | +0.234 | 1.6% | 17.2% | -15.6pp | 3.79s/q | 12.49s/q | 3.29x | 16.9s | 5m 04s | 45.6K | 55.4K |
| 190d | 5.343 | 5.114 | +0.229 | 0.0% | 14.3% | -14.3pp | 3.68s/q | 13.54s/q | 3.68x | 18.5s | 5m 56s | 47.9K | 58.4K |
| 200d | 5.159 | 5.127 | +0.032 | 3.2% | 19.0% | -15.9pp | 3.68s/q | 12.13s/q | 3.30x | 19.3s | 6m 28s | 47.2K | 57.4K |
| 210d | 5.179 | 4.881 | +0.299 | 1.5% | 20.9% | -19.4pp | 3.59s/q | 13.54s/q | 3.77x | 20.8s | 6m 48s | 49.7K | 60.5K |
| 220d | 5.145 | 4.839 | +0.306 | 1.6% | 24.2% | -22.6pp | 3.83s/q | 12.74s/q | 3.33x | 20.9s | 7m 13s | 46.9K | 56.8K |
| 230d | 5.293 | 4.845 | +0.448 | 0.0% | 17.2% | -17.2pp | 3.84s/q | 13.09s/q | 3.41x | 22.2s | 7m 48s | 47.3K | 57.4K |
| 240d | 5.329 | 5.096 | +0.233 | 1.4% | 16.4% | -15.1pp | 3.75s/q | 13.19s/q | 3.52x | 23.2s | 7m 57s | 46.5K | 56.2K |
| 250d | 5.207 | 5.534 | -0.328 | 5.2% | 8.6% | -3.4pp | 3.67s/q | 13.35s/q | 3.63x | 24.2s | 8m 46s | 47.9K | 58.3K |
| 260d | 5.000 | 5.014 | -0.014 | 5.7% | 18.6% | -12.9pp | 3.76s/q | 14.85s/q | 3.95x | 26.1s | 9m 11s | 48.4K | 58.9K |
| 270d | 5.419 | 4.984 | +0.435 | 6.5% | 17.7% | -11.3pp | 3.82s/q | 15.17s/q | 3.98x | 26.6s | 10m 01s | 51.0K | 61.8K |
| 280d | 4.910 | 4.896 | +0.015 | 6.0% | 22.4% | -16.4pp | 3.75s/q | 13.97s/q | 3.72x | 27.2s | 10m 39s | 46.7K | 56.4K |
| 290d | 5.161 | 5.081 | +0.081 | 9.7% | 17.7% | -8.1pp | 4.14s/q | 13.77s/q | 3.33x | 29.2s | 10m 57s | 47.7K | 58.2K |
| 300d | 5.339 | 4.559 | +0.780 | 1.7% | 27.1% | -25.4pp | 3.74s/q | 15.01s/q | 4.01x | 29.4s | 10m 32s | 50.5K | 61.5K |
| 310d | 5.347 | 5.361 | -0.014 | 1.4% | 6.9% | -5.6pp | 3.75s/q | 14.63s/q | 3.91x | 31.2s | 13m 45s | 48.6K | 58.8K |
| 320d | 5.070 | 5.123 | -0.053 | 7.0% | 17.5% | -10.5pp | 3.78s/q | 12.60s/q | 3.33x | 32.1s | 13m 02s | 47.1K | 57.2K |
| 330d | 5.000 | 4.946 | +0.054 | 4.1% | 17.6% | -13.5pp | 3.72s/q | 15.45s/q | 4.15x | 32.9s | 15m 07s | 43.5K | 52.7K |
| 340d | 4.730 | 4.889 | -0.159 | 4.8% | 19.0% | -14.3pp | 4.09s/q | 15.34s/q | 3.75x | 33.5s | 15m 53s | 49.0K | 59.6K |
| 350d | 5.000 | 5.046 | -0.046 | 3.2% | 16.9% | -13.7pp | 4.22s/q | 16.25s/q | 3.86x | 34.8s | 14m 05s | 49.9K | 60.6K |
| 360d | 5.113 | 4.823 | +0.290 | 4.8% | 19.4% | -14.5pp | 4.01s/q | 15.84s/q | 3.95x | 35.9s | 14m 18s | 50.1K | 60.7K |
| 370d | 5.190 | 4.841 | +0.349 | 4.8% | 22.2% | -17.5pp | 3.89s/q | 14.90s/q | 3.83x | 37.4s | 12m 21s | 47.1K | 57.0K |
| 380d | 4.618 | 5.013 | -0.395 | 10.5% | 10.5% | +0.0pp | 3.96s/q | 17.18s/q | 4.34x | 38.6s | 14m 35s | 44.2K | 53.5K |
| 390d | 4.548 | 4.855 | -0.306 | 12.9% | 17.7% | -4.8pp | 4.16s/q | 13.84s/q | 3.33x | 38.8s | 12m 23s | 46.4K | 56.4K |
| 400d | 4.691 | 5.059 | -0.368 | 7.4% | 16.2% | -8.8pp | 4.24s/q | 15.47s/q | 3.65x | 39.8s | 12m 47s | 46.0K | 55.8K |
| 410d | 4.921 | 5.222 | -0.302 | 6.3% | 15.9% | -9.5pp | 4.03s/q | 14.22s/q | 3.53x | 40.6s | 14m 44s | 47.0K | 57.1K |
| 420d | 5.273 | 5.000 | +0.273 | 1.5% | 22.7% | -21.2pp | 4.05s/q | 14.14s/q | 3.49x | 40.5s | 15m 25s | 47.9K | 58.2K |
| 430d | 5.226 | 5.339 | -0.113 | 4.8% | 11.3% | -6.5pp | 3.84s/q | 14.53s/q | 3.78x | 42.2s | 17m 49s | 46.7K | 56.5K |
| 440d | 5.111 | 4.825 | +0.286 | 7.9% | 20.6% | -12.7pp | 3.97s/q | 15.16s/q | 3.81x | 44.5s | 13m 55s | 45.7K | 55.2K |
| 450d | 5.071 | 4.690 | +0.381 | 2.9% | 23.9% | -21.1pp | 4.06s/q | 15.63s/q | 3.85x | 45.1s | 16m 25s | 46.6K | 56.3K |
| 460d | 4.787 | 4.770 | +0.016 | 11.5% | 21.3% | -9.8pp | 4.49s/q | 15.48s/q | 3.45x | 44.2s | 19m 09s | 49.4K | 59.7K |
| 470d | 4.574 | 5.103 | -0.529 | 13.2% | 13.2% | +0.0pp | 4.21s/q | 16.23s/q | 3.85x | 47.3s | 19m 39s | 47.7K | 57.9K |
| 480d | 5.048 | 5.161 | -0.113 | 4.8% | 12.9% | -8.1pp | 4.04s/q | 18.05s/q | 4.47x | 46.8s | 19m 30s | 51.2K | 62.0K |
| 490d | 4.928 | 5.000 | -0.072 | 13.0% | 15.9% | -2.9pp | 3.96s/q | 16.40s/q | 4.14x | 49.7s | 21m 32s | 47.4K | 57.0K |
| 500d | 4.608 | 4.730 | -0.122 | 12.2% | 27.0% | -14.9pp | 4.12s/q | 17.46s/q | 4.23x | 50.2s | 21m 16s | 50.8K | 61.5K |

Notes: `CF Tokens/Q` and `CF Retrieved/Q` are ContextForge answer-model diagnostics only. The OpenClaw folder contains `progress.jsonl`, `result.json`, `failures.jsonl`, and `heatmap.png`, but no comparable token diagnostics file.
