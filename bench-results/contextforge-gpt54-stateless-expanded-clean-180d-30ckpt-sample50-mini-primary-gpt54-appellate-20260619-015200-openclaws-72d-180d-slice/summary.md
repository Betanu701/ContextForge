# ContextForge OpenClaws 180d Slice

Source run: `/home/derek/repo/ContextForge/bench-results/contextforge-gpt54-stateless-expanded-clean-180d-30ckpt-sample50-mini-primary-gpt54-appellate-20260619-015200`
Slice ranges: `72d, 78d, 84d, 90d, 96d, 102d, 108d, 114d, 120d, 126d, 132d, 138d, 144d, 150d, 156d, 162d, 168d, 174d, 180d`

| Metric | ContextForge | OpenClaws | Delta |
|---|---:|---:|---:|
| Checkpoints | 19 | 19 | +0 |
| Questions evaluated | 1125 | 1212 | -87 |
| Weighted score | 4.832/6 (80.5%) | 5.450/6 (90.8%) | -0.618/6 (-10.3 pts) |
| Hallucination rate | 7.9% | 8.5% | -0.6 pts |
| Speed | 3.17s/eval | 10.82s/eval | -7.65s/eval |
| Speedup vs OpenClaws | 3.41x | 1.00x | +2.41x |

Artifacts:
- `progress.jsonl`
- `result.json`
- `openclaws-comparison.json`
