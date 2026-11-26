# Evidence — D81 quality (provisional) on Modal A10G

**Date:** 2026-11-26. **Profile:** Modal A10G (fp32), e5-small provisional (D81).
**Corpus:** CC-MAIN-2026-43, one WARC segment → 9625 docs, 46631 passages
(`empty_url_docs: 0`). **Golden:** 30 queries (`query_plan.jsonl`), 592 candidates
(30×20, fused dense+BM25), LLM-judged by Qwen2.5-7B-Instruct (0–3).
**Raw:** `bench/results/{golden_dev.jsonl, quality.json, corpus_manifest.json}`.
**Scripts:** `bench/modal_pipeline.py`, `bench/eval_quality.py`.

## Label distribution
0: 492 · 1: 76 · 2: 16 · 3: 8 (28/30 queries have ≥1 relevant candidate).

## Ranking quality (provisional model, D81 step 3)
| Metric | Value |
|---|---|
| nDCG@10 (mean) | **0.3885** |
| recall@10 (mean) | **0.5148** |
| MRR (mean) | **0.5315** |

## Status (provisional — D81)

- **Quality (D81 step 3):** measured provisionally on A10G/e5-small. The frozen
  D81 needs the **RTX Pro 6000 bf16** reference + a **human-calibrated judge (κ,
  §1.5/D14)** + the full T0 corpus + 100 EN dev queries (D93).
- **Caveats:** random T0 sample → sparse relevance (many 0s); LLM judge not
  human-calibrated; 30 queries (not 100); A10G fp32 (not RTX bf16).
- **Throughput (D81 step 3):** measured on A10G (`docs/evidence_d81_a10g.md`).

These advance D81 provisionally; they do **not** freeze D81 (labelled provisional
per D81/D47). The full freeze is the RTX evidence batch.