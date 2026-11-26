# T0 tokens/word & overflow report (Run B → D44)

**Date:** 2026-11-26. **Profile:** RTX Pro 6000 (Python 3.13). **Corpus:**
CC-MAIN-2026-43, single WARC segment (`…/segments/1791170053823.21/warc/…00162.warc.gz`),
first 2000 response records → 1899 docs after cleaning. **Tokenizer:**
`intfloat/multilingual-e5-small` (the hungriest D81 candidate). **Raw:**
`bench/results/run_b.json`.

## Tokens/word

| Metric | Value |
|---|---|
| words | 873,774 |
| tokens | 2,163,068 |
| **tokens/word (aggregate)** | **2.4755** |

(Aggregate ratio; the full B report would add median + p95 per language.)

## Overflow (at the provisional max 400 words)

| Metric | Value |
|---|---|
| passages | 6704 |
| passages/doc | 3.53 |
| overflow (> budget) | 114 |
| **overflow rate** | **1.7%** |
| threshold | ≤ 0.5% |

400 words × 2.4755 ≈ 990 tokens ≫ 512-token budget → **fails**. Overflow is
counted, not re-chunked (D60).

## Chosen sizes → D44

`budget_passage` ≈ 512 − special − prefix/title ≈ **490 tokens**. At 2.4755 t/w:

- **max_size = 192 words** (≈476 tok < 490) — fits the budget.
- **target_size = 128 words** (≈317 tok) — fits p99.
- **overlap = 1 sentence.**
- `chunker_version = uax29-1.0;target=128;max=192;overlap=1`.

**Caveat:** single WARC segment, aggregate tokens/word (not median/p95), no
128/256/512 size sweep. A full T0 (8k EN + 2k FR) + per-size sweep is the
confirmation (recommended, not blocking the freeze). The 400-word overflow is the
justification for lowering max_size.