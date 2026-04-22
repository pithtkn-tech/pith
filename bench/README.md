# Pith Benchmark — 1,008 Tests

Independent benchmark of Pith's compression pipeline across 1,008 test scenarios.

**Date:** April 19-20, 2026  
**Server:** Production (api.pithtoken.ai)  
**Models:** GPT-4o-mini, Claude Haiku 4.5  
**Judges:** Dual blind LLM evaluation (GPT-4o-mini + Claude Haiku, direct API — not through Pith)

---

## Summary

| Phase | Tests | What it measures |
|-------|-------|-----------------|
| ISO | 424 | Rule-based optimizer alone (18 categories) |
| E2E | 284 | Full pipeline: optimizer + LLMLingua + conversation compression |
| Judge | 300 | Per-turn quality preservation via dual LLM judges |
| **Total** | **1,008** | |

### Key results

- **ISO layer:** 7.9% mean compression, <1ms latency
- **Full pipeline:** 33.8% mean compression, 0.85 cosine similarity
- **Deep conversations (turns 8-15):** 69-77% compression, judge score 3.36-3.42/5 (3.0 = equivalent quality)
- **Quality preservation:** 87.7% of compressed responses score ≥3.0 (no degradation)
- **Compression scales with depth** — the longer the conversation, the more tokens saved, with no quality loss

---

## Directory structure

```
bench/
├── README.md                              ← you are here
└── results/
    ├── metadata.json                      ← test configuration
    ├── iso/
    │   └── iso_results.jsonl              ← 424 ISO layer results
    ├── e2e/
    │   └── e2e_all.jsonl                  ← 284 end-to-end results
    ├── judge/
    │   ├── judge_depth_results.jsonl      ← 300 per-turn judge evaluations
    │   ├── judge_summary.json             ← aggregate judge stats
    │   ├── judge_compression_vs_quality.png
    │   ├── judge_cosine_depth.png
    │   ├── judge_depth_bands.png
    │   └── judge_per_model.png
    └── analysis/
        ├── BENCHMARK_REPORT.md            ← full report with tables
        ├── summary_stats.json             ← machine-readable summary
        ├── depth_curve.json               ← compression vs depth data
        ├── compression_summary.png
        └── compression_vs_depth.png
```

---

## Data formats

### ISO results (`iso_results.jsonl`)

Each line is one test — a single prompt category evaluated for rule-based compression:

```json
{
  "category": "coding",
  "compression_ratio": 0.103,
  "original_tokens": 245,
  "compressed_tokens": 220
}
```

### E2E results (`e2e_all.jsonl`)

Each line is one end-to-end test — full pipeline with conversation depth:

```json
{
  "category": "depth_t10",
  "model": "gpt-4o-mini",
  "compression_ratio": 0.691,
  "cosine_similarity": 0.827,
  "latency_ms": 1805,
  "turns": 10
}
```

### Judge results (`judge_depth_results.jsonl`)

Each line is one per-turn evaluation — dual LLM judges score the compressed response:

```json
{
  "turn": 8,
  "mode": "balanced",
  "model": "gpt-4o-mini",
  "compression_pct": 60.9,
  "judge_gpt": 3.5,
  "judge_claude": 3.1,
  "judge_avg": 3.3,
  "cosine": 0.814
}
```

**Judge scale:** 1 = much worse, 2 = somewhat worse, 3 = equivalent, 4 = somewhat better, 5 = much better

---

## Compression vs. depth

| Depth band | Compression (balanced) | Compression (aggressive) | Judge score |
|------------|----------------------|------------------------|-------------|
| Early (turns 1-3) | 3.7% | 3.8% | 3.28 |
| Mid (turns 4-7) | 41.7% | 64.4% | 3.37 |
| Deep (turns 8-15) | 69.1% | 76.9% | 3.39 |

Compression increases with conversation depth. Quality remains constant.

---

## Reproduce

These results were generated against Pith's production API. The test harness used:

1. **LMSYS-Chat-1M** prompts (curated multi-turn conversations)
2. **Three compression modes:** conservative, balanced, aggressive
3. **Two models:** GPT-4o-mini, Claude Haiku 4.5
4. **Dual blind judging:** Both judges evaluate without knowing which response is compressed

Full methodology: [`results/analysis/BENCHMARK_REPORT.md`](results/analysis/BENCHMARK_REPORT.md)

---

## License

Benchmark data is released under Apache 2.0, same as the main project.
