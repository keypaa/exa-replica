# S4 — B Protocol: Tokens/Word & Overflow (extends B)

**Status:** measurement tooling (allowed before design freeze, D35). Extends `s4_t0_extractor_protocol.md`.
**Goal:** convert reference-unit sizes (words) into model tokens per candidate, and measure the overflow rate per candidate passage size — the inputs to freeze the passage spec (D44) and the D65 embedding budget.
**Rule:** thresholds are fixed **before** the run; the report is the evidence.

---

## 1. B prerequisites (must exist before the run)

- [ ] **T0 extracted** — CC-MAIN-2026-43, columnar index + range requests (D28); 8k EN + 2k FR (D30).
- [ ] **Language detection in place** — D76, `lang` field populated, `und` handled.
- [ ] **Cleaning in place** — D77, NFC-normalized `text_canonical`.
- [ ] **Tokenizer frozen** — the S5 candidate tokenizers at pinned HF revisions (D57/D58).
- [ ] **Buckets provisioned** — `exa-replica-corpus` + `exa-replica-artifacts` (D38/D40); quota guard (D38).
- [ ] **Golden set** — frozen (D33/D13); relevant docs present in T0.
- [ ] **Thresholds frozen** — `s4_b_thresholds.md` (sha256 `4c9804f7…eeee`) + the tokens/word + overflow thresholds below.

If any box is unchecked, B runs on data that does not match the final version → results invalid.

---

## 2. Sample

- Stratified by language: **~200 docs per main language** (EN, FR), random within the T0 strata.
- Plus the golden-set docs present in T0 (for the overflow check on real relevant content).

---

## 3. Metrics

### 3.1 Tokens/word ratio
- For each **candidate tokenizer** (Qwen3, arctic v2, EmbeddingGemma 2 — D58) and each language:
  - **median** and **p95** tokens per reference-unit word (UAX #29, D60);
  - total tokens per doc.
- Output: a **table per language × candidate**.

### 3.2 Overflow rate
- For each candidate passage size (**128 / 256 / 512 words**) and each candidate tokenizer:
  - share of passages whose token count exceeds `budget_passage` (D60) → **truncated at embedding**;
  - p99 token count per size.
- Overflow is **counted, not re-chunked** (D60).

---

## 4. Thresholds (fixed before the run)

| Criterion | Threshold (proposal) | Action if failed |
|---|---|---|
| Overflow rate | **≤ 0.5%** of passages per size | lower `target_size` or shorten doc prefix |
| p99 fit | p99 tokens ≤ `budget_passage` for the hungriest candidate | lower `target_size` |
| Coverage | ≥ 1 passage for ≥ 99% of docs | investigate min-length / cleaning |

> These are **proposals**; freeze before the run (append to `s4_b_thresholds.md` or a new frozen file).

---

## 5. Report

Write `docs/research/t0-tokens-report.md`:
- Date, corpus hash, tokenizer revisions, sample sizes.
- Tokens/word table (language × candidate; median + p95).
- Overflow table (size × candidate; rate + p99).
- Chosen `target_size` / `max_size` / `overlap` recommendation → feeds **D44**.

---

## 6. What this unblocks

- **D44** passage spec frozen (target/max/overlap in words, with token budgets per candidate).
- **D65** embedding-time estimate (tokens of T1 ÷ T0 tokens/s).
- **S6** vector count `N_docs × r` and the 500 GB split (D73).