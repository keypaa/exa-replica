# Evidence — D81 throughput on A10G (provisional)

**Profile:** Modal A10G (see `docs/hardware_reference.md`). **Date:** 2026-11-26.
**Config:** sentence-transformers 3.1.1, transformers 4.46.3, torch 2.4.1, **fp32**
(default), 2000 passages (8× repeated lorem), 200 queries, batch 32/64/128/256.
**Raw:** `bench/results/modal_d81_a10g.json` / `.txt`. **Script:** `bench/modal_d81.py`.

| Model | dim | bs32 | bs64 | bs128 | bs256 | query p95 |
|---|---|---|---|---|---|---|
| intfloat/multilingual-e5-small | 384 | 2451 | 2949 | 3251 | 3450 | 7.1 ms |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | 384 | 2399 | 2850 | 3115 | 3335 | 6.8 ms |
| intfloat/multilingual-e5-base | 768 | 997 | 1120 | 1130 | 943 | 7.4 ms |
| Alibaba-NLP/gte-multilingual-base | 768 | — | — | — | — | failed (custom `gte` arch; needs `trust_remote_code`/newer transformers) |

Throughput in passages/s. All query p95 ≪ 50 ms (D66).

## Status (provisional — D81)

- **Throughput filter (D81 step 3):** measured on A10G fp32 (lower bound). The frozen
  reference is the **RTX Pro 6000 bf16** (D36); re-measure there before freezing.
- **Query p95 (D66 ≤50 ms):** passes on A10G for all measured candidates.
- **Quality (D81 step 3 nDCG@10):** **not measured** — needs the judged golden set
  (evidence-blocked: real candidates need the T0 corpus on RTX).
- **gte-multilingual-base:** retry with `trust_remote_code=True` or a newer transformers.

These numbers advance the D81 shortlist provisionally; they do **not** freeze D81
(labelled provisional per D81/D47).