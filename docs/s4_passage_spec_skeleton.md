# S4 — Passage Spec Skeleton (A, pre-B)

**Status:** skeleton. Every numeric value is **`TBD-B`**. Frozen as **D44** only after the B measurements.
**Rule:** the chunker is deterministic; same `text_canonical` + same `chunker_version` → same passages, bit-exact.
**Amendment (D60):** the chunking unit is **model-independent** (default **UAX #29 words/sentences**); the embedding-model tokenizer is a **constraint only**, never part of `chunker_version`.

---

## 1. Parameters (`TBD-B`; provisional defaults in **bold**)

**Unit is the reference unit (UAX #29 words), not tokens (D60).** The provisional defaults below are in **words**; token equivalents (~1.3 token/word EN, more in FR) are indicative only and confirmed by B.

| Parameter | Value | Notes |
|---|---|---|
| `target_size` | `TBD-B` (**~180–200 words** ≈ 256 tokens EN) | candidates 128 / 256 / 512 **tokens** → converted to words by B |
| `overlap` | `TBD-B` (**1 sentence**) | may be 0 |
| `min_size` | `TBD-B` | below → merge with previous/next |
| `max_size` | `TBD-B` (**~350–400 words** ≈ 512 tokens EN) | hard cap; also ≤ reranker `max_pair_tokens` − max query (D67) |
| `reference_unit` | **UAX #29 words** + version | part of `chunker_version` (D60) |
| `sentence_splitter` + version | language-specific (EN/FR) | part of `chunker_version` |
| `title_prefix` | index config | **not** in the chunker; doc template decides placement (D61) |
| `model_tokenizer` | from S5 | **constraint only** → `budget_passage`; **not** in `chunker_version` |

**Criterion to freeze the values from B (D47):** choose the largest candidate size whose **p99 token count ≤ `budget_passage` for the hungriest candidate** (D60), with **overflow ≤ threshold** (§8). No default is frozen until B produces this.

**`budget_passage` (D60):** `max_tokens_effective − special tokens − doc prefix − title`.
The target size must fit **p99** for the hungriest candidate (measured in B). Residual overflow is **truncated at embedding**, no re-chunk, with a max threshold.

---

## 2. Identity & offsets

- `passage_id` = (`url_canonical`, `generation`, `content_hash`, `chunker_version`, ordinal).
- `chunker_version` = reference unit + version + sentence-splitter version + numeric parameters. **Excludes the model tokenizer** (D60).
- Offsets `[start, end)` are on `text_canonical` (**NFC-normalized**, D77), in **UTF-8 bytes** (D78).
- Token↔byte conversion: reference-unit offsets → tokenizer offset mapping → code points → UTF-8 bytes. **Tested on accented text** (French).

---

## 3. Boundary cascade

1. **Paragraph** (`\n\n`).
2. **Sentence** (language-specific splitter, versioned; UAX #29).
3. **Hard cut** at a reference-unit boundary — never inside a UTF-8 character.

A document with no `\n\n` is one huge paragraph → sentence/hard cut.

---

## 4. Merge rules

- A passage shorter than `min_size` is merged with the **previous**; if there is no previous, with the **next**.
- A merge must not exceed `max_size`; if it would, keep the passage as-is or re-split (decision `TBD-B`).
- A document shorter than `min_size` → one passage, or excluded with a reason code (per schema rule).
- **Never zero passages without a reason code.**

---

## 5. Overlap & title

- Adjacent `[start, end)` may overlap by `overlap`; highlights and result dedup must account for it.
- The title is added at **index time** via `title_prefix` (index config), not in the passage text; `passage_id` is unchanged. The **doc template** (D61) decides where the title goes; `title_prefix` only decides whether to fill it.

---

## 6. Determinism

- Same `text_canonical` + `chunker_version` → same passages, bit-exact.
- Test: golden hash of passages for a fixture.

---

## 7. Tests

- Determinism (golden hash).
- UTF-8 offsets on accented text (NFC).
- No empty passage.
- Merge behavior (short first/middle/last).
- Overlap.
- Hard cut never splits a UTF-8 character.
- `chunker_version` changes when the **reference unit/splitter/params** change (not when the model changes, D60).

---

## 8. B threshold operational definitions (to freeze before the run)

| Threshold | Operational definition |
|---|---|
| Throughput | docs/s **per core**; state whether it includes WARC read + gzip decode + HTML parse, or extraction only. Convert T1 ≤12 h to a docs/s/core target. |
| Main text retained | per-doc rating: **OK / partial loss / major loss**; threshold on the **share of major loss** (not characters). |
| Boilerplate | per-doc rating or per-line share; one common grid. |
| Golden-set emptied | the passage containing the answer is **absent** from `text_canonical` (not just zero length). |
| Metadata | per field, only **when the data exists in the page**; a wrong date (crawl date as publication) counts more than an absence. |
| Exceptions | distinguish crash / timeout / empty output. |
| Readability | optional; not a D42 candidate (trafilatura vs resiliparse only). |
| Tokens/word | median + p95 per candidate tokenizer and per language (see `s4_b_tokens_protocol.md`). |
| Overflow rate | share of passages truncated at embedding, per candidate size; must stay ≤ threshold. |

**Statistical note:** 50 docs/language → ±6–8 points CI; the review detects gross failures, not fine ranking. Throughput + golden-set control weigh more in D42.