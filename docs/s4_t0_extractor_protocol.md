# S4 — T0 Extractor Validation Protocol (B)

**Status:** measurement tooling (allowed before design freeze, D35).
**Goal:** validate **trafilatura** (D42) against the fallback **resiliparse**, and collect the measurements needed to freeze the passage spec (A → D44).
**Rule:** thresholds are fixed **before** the run; the report is the evidence.

---

## 1. Sample

- **Corpus:** T0 from **CC-MAIN-2026-43**, selected via the columnar index + range requests (D28).
- **T0 composition:** 8k EN + 2k FR (D30).
- **Throughput sample:** all T0 (~10k docs).
- **Manual review sample:** 50 EN + 50 FR, random, stratified by domain.
- **Golden-set subset:** the relevant docs for the 50–100 query set, if present in T0; plus the target docs.

---

## 2. Metrics

### 2.1 Throughput
- Wall time, docs/s total, docs/s per core, per language.
- Extractors: trafilatura (default), resiliparse (fallback), readability (reference only).

### 2.2 Extraction quality (manual review, 50/lang)
- Main text retained (yes/no).
- Boilerplate remaining (none / minor / major).
- Title, author, date present (where available).
- Text loss (content missing vs WARC HTML).
- Golden-set docs emptied (count).

### 2.3 Length distributions (for A)
- Document length: characters and tokens (candidate tokenizers from S5).
- Paragraph length (split on `\n\n`): characters/tokens; share of very short paragraphs; share above a target passage size.
- Share of documents that fit in a single passage.
- Passages per document for candidate sizes **128 / 256 / 512 tokens** → estimate ratio `r` (D29).
- Position of relevant content in golden-set docs (start / middle / end) → informs overlap and title prefixing.

### 2.4 Failures
- Exceptions, empty text, undecodable, invalid URL, `canon_collision`.

---

## 3. Thresholds (fixed before the run)

| Criterion | Threshold | Action if failed |
|---|---|---|
| Throughput | T1 (1M docs) ≤ **12 h** on 16 vCPU (~23 docs/s total) | fallback resiliparse for text + separate metadata |
| Main text retained | ≥ **95%** of reviewed docs | investigate extractor config |
| Boilerplate remaining | ≤ **5%** of reviewed docs | investigate |
| Golden-set docs emptied | **0** | block; fix extractor |
| Metadata present | title/author/date for ≥ **80%** where available | accept with `null` + reason |
| Exceptions | ≤ **1%** of docs | investigate |

> The 12 h / 95% / 5% / 0 / 80% / 1% values are **proposals**; freeze them before the run.

---

## 4. Report

Write `docs/research/t0-extractor-report.md`:
- Date, corpus hash, sample sizes, extractor versions.
- Per-extractor metrics table.
- Manual review results (per language).
- Length distributions (docs, paragraphs).
- Passage ratio table (128/256/512).
- Golden-set position.
- Decision: trafilatura confirmed, or fallback resiliparse + separate metadata.
- Open items for A (D44).

---

## 5. What this unblocks

- **D42** confirmed or fallback.
- **D44** passage spec with real numbers (token size, overlap, min length, ratio r).
- The passage spec skeleton (passage_id, offsets, title at index time, short-passage merge) can be written now, without numbers.