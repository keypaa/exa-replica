# M1 Contract e2e Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `/search` (lite+auto) + `/contents` (highlights S0) and both MCP tools end-to-end on a small corpus, passing Gate 0 (D12) and Gate 1 (MCP drop-in, replica).

**Architecture:** Full pipeline on a minimal single-process topology (D89): ingest → clean → chunk → content store → BM25 (Tantivy) + dense R0 (GPU bf16) → RRF fusion → highlights S0. Provisional embedding model (D81). Reranker passthrough (no reorder) on T0.

**Tech Stack:** Python 3.12, trafilatura, Tantivy (tantivy-py), PyTorch (bf16), FastAPI, `mcp` 2.x, Parquet/zstd.

**Spec:** `docs/EXA_REPLICA_RESEARCH.md` (D19/D28–D56, D60, D70, D81–D84, D94), `docs/s2_contract_matrix.md`, `docs/s4_passage_spec_skeleton.md`, `docs/s4_manifest_schemas_v0.md`.

## Global Constraints

- Provisional model (D81): no dev golden set → labelled provisional, cannot enter a frozen spec.
- Passage unit = UAX #29 words (D60); `chunker_version` excludes model tokenizer.
- BM25 k1=1.2, b=0.75 (D83); EN/FR two-field (D83).
- Dense R0 exact GPU bf16 (D82); dims = provisional model.
- Filters before fusion; no out-of-filter result (D70).
- Highlights S0 extractive (D84); no LLM.
- No live fetch (D56); `/contents` reads the snapshot; `not_in_index` split on the fly.
- `degraded` single field (D69); `unsupported_field` 400 (D27); `X-Index-Version` + 409 (D99).

## Review Focus

- **Empty document:** no `text_canonical` → excluded with reason code, never zero passages silently (D60/D77, §4.1.2). Test in Task 3.
- **Non-UTF8 / accents:** offsets in UTF-8 bytes on NFC text; French accents not cut (D78). Test in Task 3.
- **Filter after fusion:** an out-of-filter result must never appear (D70). Test in Task 7.
- **Cache/takedown:** excluded doc absent at serving (D52); the warm-cache variant is tested in M5 (D90). Test in Task 9.
- **`not_in_index` duplicate:** highlights still produced from stored text (D84). Test in Task 8.

---

### Task 1: Document schema + canonical text + extractor + canon-v1

**Files:**
- Create: `src/exa_replica/domain/document.py`, `adapters/outbound/extract.py`; Test: `tests/domain/test_document.py`, `tests/adapters/test_extract.py`

**Interfaces:**
- Produces: `Document` (id, url_canonical, lang, content_hash, text_canonical, published_date, …); `extract(html, warc_date) -> Document`; `canon_v1(url) -> str`.

- [ ] **Step 1: Write failing test** `test_canon_v1_no_www_merge`, `test_extract_fills_lang_and_date`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement `Document`, `canon_v1` (D43), trafilatura extractor (D42) with resiliparse fallback.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: document schema + extractor + canon-v1 (D41/D42/D43)`.

### Task 2: Cleaning + language detection (D76/D77)

**Files:**
- Create: `adapters/outbound/clean.py`, `adapters/outbound/lang.py`; Test: `tests/adapters/test_clean.py`, `tests/adapters/test_lang.py`

**Interfaces:**
- Consumes: `Document`. Produces: `clean(doc) -> Document` (NFC, control chars, min len, exact dedup); `detect_lang(text) -> str` (`und` below threshold).

- [ ] **Step 1: Write failing test** `test_nfc_normalization`, `test_short_doc_excluded_with_reason`, `test_und_below_threshold`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement cleaning order (D77) + GlotLID (D76).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: cleaning + language detection (D76/D77)`.

### Task 3: Passage chunker (D60, provisional)

**Files:**
- Create: `application/chunker.py`; Test: `tests/application/test_chunker.py`

**Interfaces:**
- Consumes: `Document`. Produces: `list[Passage]` with `[start,end)` UTF-8 bytes; `chunker_version`.

- [ ] **Step 1: Write failing test** `test_offsets_utf8_on_accents`, `test_no_empty_passage`, `test_determinism_golden_hash`, `test_empty_doc_reason`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement UAX #29 chunker with provisional defaults (~180–200 words / max ~350–400, 1-sentence overlap).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: passage chunker (D60)`.

### Task 4: Content store + docstore (D48–D50)

**Files:**
- Modify/implement: `adapters/outbound/store.py` (stub from M0); Test: `tests/adapters/test_store.py`

**Interfaces:**
- Consumes: `Document`, `Passage`. Produces: `ContentStore.put/get`; `docstore` mapping `id → (shard, row group, row)`.

- [ ] **Step 1: Write failing test** `test_roundtrip_text`, `test_passage_offsets_only`, `test_shard_by_hash`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement Parquet shards + mapping (D48–D50), zstd.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: content store + docstore (D48–D50)`.

### Task 5: BM25 index (D83)

**Files:**
- Create: `adapters/outbound/bm25.py`; Test: `tests/adapters/test_bm25.py`

**Interfaces:**
- Consumes: `Passage`. Produces: `LexicalIndex` (Tantivy) with `text_en`/`text_fr`, k1=1.2/b=0.75.

- [ ] **Step 1: Write failing test** `test_bm25_finds_relevant`, `test_en_fr_fields`, `test_k1_b_frozen`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement Tantivy index (D83) with global stats.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: BM25 index (D83)`.

### Task 6: Dense R0 + provisional embedding (D82/D81)

**Files:**
- Modify/implement: `adapters/outbound/encoder.py`, `adapters/outbound/ann.py` (stubs from M0); Test: `tests/adapters/test_dense.py`

**Interfaces:**
- Consumes: `Passage`. Produces: `DenseIndex` R0 (bf16, exact GPU), `Embedder.embed(texts)`.

- [ ] **Step 1: Write failing test** `test_r0_exact_topk`, `test_query_encode`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement R0 (D82) with provisional model (D81, bf16, PromptConfig D61).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: dense R0 + provisional embedding (D81/D82)`.

### Task 7: Fusion RRF + winning passage (D81/D83)

**Files:**
- Create: `application/fusion.py`; Test: `tests/application/test_fusion.py`

**Interfaces:**
- Consumes: BM25 + dense. Produces: `fuse(bm25_hits, dense_hits) -> list[DocHit]` with winning `passage_id`.

- [ ] **Step 1: Write failing test** `test_rrf_k60`, `test_winning_passage`, `test_no_out_of_filter_result`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement RRF (k=60) + winning passage (D83 A).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: RRF fusion + winning passage (D81/D83)`.

### Task 8: Highlights S0 (D84)

**Files:**
- Create: `application/highlights.py`; Test: `tests/application/test_highlights.py`

**Interfaces:**
- Consumes: reference passage + doc text (offsets). Produces: `highlights(text, guiding) -> list[str]`.

- [ ] **Step 1: Write failing test** `test_s0_first_sentences`, `test_not_in_index_split`, `test_nosnippet_empty`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement S0 extractive (D84) + D51 directives.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: highlights S0 (D84)`.

### Task 9: HTTP /search + /contents + MCP tools (D8/D22/D23)

**Files:**
- Modify/implement: `adapters/inbound/http.py`, `adapters/inbound/mcp.py`, `adapters/outbound/contents.py` (ContentsProvider, stub from M0); Test: `tests/adapters/test_http.py`, `tests/adapters/test_mcp.py`

**Interfaces:**
- Consumes: `SearchService`, `ContentStore`, highlights, `ContentsProvider` (`contents.py`). Produces: `/search` (lite/auto), `/contents`, MCP `web_search_exa`/`web_fetch_exa`.

- [ ] **Step 1: Write failing test** `test_search_lite`, `test_search_auto`, `test_contents_xor`, `test_mcp_tools`, `test_unsupported_field_400`, `test_index_version_mismatch_409`, `test_takedown_served`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement HTTP + MCP on same ASGI app (D8/D22/D23/D99).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: HTTP + MCP surface (D8/D22/D23)`.

### Task 10: Gate 0 (D12) + Gate 1 (§1.1) tests

**Files:**
- Create: `tests/gate/test_gate0.py`, `tests/gate/test_gate1.py`

**Interfaces:**
- Consumes: full M1 surface. Produces: passing Gate 0 + Gate 1 (replica).

- [ ] **Step 1: Write failing test** `test_gate0_core_api`, `test_gate1_mcp_dropin`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Wire fixtures (toy corpus) to satisfy both.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `test: Gate 0 + Gate 1 (D12)`.