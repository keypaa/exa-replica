# S4 — Manifest Schemas v0 (draft, not frozen)

**Status:** draft v0. Freeze as `manifest-schema-v1` before the first T1 build.
**Rule:** `build_id` and stage keys are hashes of the **spec only** (JCS). Results/timestamps go in the result, written last (D46).

---

## 1. Corpus manifest (`corpus-<generation>.json`)

```json
{
  "schema_version": "corpus-manifest/v0",
  "generation": "CC-MAIN-2026-43-g1",
  "crawl_id": "CC-MAIN-2026-43",
  "warc_paths_sha256": "…",
  "columnar_index": {
    "url": "https://data.commoncrawl.org/…/cc-index/table/cc-main/warc/",
    "sha256": "…",
    "columns": ["url", "lang", "status", "mime", "warc_file", "offset", "length"]
  },
  "filters": {"status": 200, "mime": "text/html", "languages": ["eng", "fra"]},
  "ratio": {"en": 0.8, "fr": 0.2},
  "seed": 0,
  "permutation_salt": "…",
  "tiers": {"t0": 10000, "t1": 1000000},
  "canonicalization": "canon-v1",
  "records": [{"warc_file": "…", "offset": 0, "length": 0, "sha256": "…"}],
  "counts": {"selected": 0, "excluded": {"invalid_url": 0, "canon_collision": 0, "dup_of": 0}}
}
```

---

## 2. Build spec (`build-<build_id>-spec.json`)

```json
{
  "schema_version": "build-spec/v0",
  "build_id": "<sha256 of canonical spec>",
  "generation": "CC-MAIN-2026-43-g1",
  "corpus_manifest_sha256": "…",
  "index_format_version": "1",
  "stages": [
    {"name": "extract", "impl_version": "trafilatura@1", "config": {}},
    {"name": "chunk", "impl_version": "chunker@3", "config": {"target_tokens": "TBD-B"}},
    {"name": "embed", "impl_version": "embed@1", "model": {"id": "…", "revision": "…", "dim": 256}, "config": {}},
    {"name": "pq", "impl_version": "pq@1", "config": {}},
    {"name": "bm25", "impl_version": "bm25@1", "config": {}}
  ]
}
```

**`build_id = sha256(JCS(spec))`.** `code_sha` is **not** in the spec.

---

## 3. Build result (`build-<build_id>-result.json`)

```json
{
  "schema_version": "build-result/v0",
  "build_id": "…",
  "generation": "CC-MAIN-2026-43-g1",
  "status": "complete",
  "stages": [
    {"name": "extract", "outputs": {"docs": "artifacts/extract/<hash>/docs.jsonl"}, "counts": {"in": 0, "kept": 0, "excluded": {}}, "seconds": 0}
  ],
  "created_at": "2026-11-25T…Z",
  "run_record": "run-<id>.json"
}
```

Written **last** (validity marker, D32).

---

## 4. Artifact manifest (`artifacts-<hash>.json`)

```json
{
  "schema_version": "artifact-manifest/v0",
  "stage": "embed",
  "hash": "…",
  "files": [{"path": "artifacts/embed/<hash>/vecs.npy", "size": 0, "sha256": "…"}]
}
```

---

## 5. Run record (`run-<id>.json`)

```json
{
  "schema_version": "run-record/v0",
  "run_id": "…",
  "build_id": "…",
  "machine": {"gpu": "RTX Pro 6000", "vram_gb": 96, "ram_gb": 128, "vcpus": 16, "disk": "500 GB NVMe ephemeral"},
  "code_sha": "…",
  "command": "…",
10. "started_at": "…",
  "ended_at": "…",
  "status": "completed",
  "metrics": {},
  "logs": "…"
}
```

---

## 6. Rules

- **Canonical JSON:** RFC 8785 (JCS) for every hash; versioned JSON Schema per document.
10. **`build_id`** = `sha256(JCS(spec))`.
10. **Stage key** = `sha256(JCS(stage_spec + input_stage_keys))` (D32).
10. **`content_hash`** = `sha256(utf8(text_canonical))` after normalization.
10. **References by hash**, not path; bucket paths derive from the hash.
10. **Counts with reason codes:** `in`, `kept`, `excluded{reason}`; they must add up.
10. **`schema_version`** in every document.
10. **Result written last;** no manifest = not valid.
10. **Validation at load:** `schema_version`, `index_format_version`, hashes.
10. **Determinism test:** same spec, new code, identical output hashes; if they differ without an `impl_version` bump → bug.

---

## 7. Open

- Exact JSON Schema files (v1).
10. Example filled for T0.
10. `impl_version` bump policy.
10. Retention of old builds (current + previous + gate-referenced).