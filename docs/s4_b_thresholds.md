# S4 — B Thresholds (frozen)

**Status:** frozen 2026-11-25. **Scope:** T0 extractor validation (trafilatura vs resiliparse fallback).
**Rule:** these thresholds are fixed before the run; the report is the evidence.

---

## 1. Sample

- **T0:** 8k EN + 2k FR (D30), from CC-MAIN-2026-43 (D28).
- **Throughput:** all T0 (~10k docs).
- **Manual review:** 50 EN + 50 FR, random, stratified by domain.
- **Golden-set subset:** relevant docs for the 50–100 query set, if present in T0.

---

## 2. Thresholds & operational definitions

| Criterion | Threshold | Operational definition |
|---|---|---|
| Throughput | T1 (1M docs) ≤ **12 h** on 16 vCPU | docs/s **per core**, including WARC read + gzip decode + HTML parse + extraction. Convert: ~23 docs/s total → ~1.44 docs/s/core. |
| Main text retained | **major loss ≤ 5%** of reviewed docs | per-doc rating: OK / partial loss / major loss. |
| Boilerplate | **major ≤ 5%** of reviewed docs | per-doc rating: none / minor / major. |
| Golden-set emptied | **0** | the passage containing the answer is **absent** from `text_canonical` (not just zero length). |
| Metadata | ≥ **80%** present **where the data exists** | per field; a wrong date (crawl date as publication) counts as an error, not an absence. |
| Exceptions | ≤ **1%** | distinguish crash / timeout / empty output. |
| Readability | optional | not a D42 candidate (trafilatura vs resiliparse only). |

**Statistical note:** 50 docs/language → ±6–8 points CI. The review detects gross failures, not fine ranking. Throughput + golden-set control weigh more in D42.

---

## 3. Review grid (per doc)

| Field | Values |
|---|---|
| `url` | — |
| `lang` | eng / fra |
| `extractor` | trafilatura / resiliparse |
| `main_text` | OK / partial / major |
| `boilerplate` | none / minor / major |
| `title_present` | yes / no |
| `author_present` | yes / no / n/a |
| `date_present` | yes / no / n/a |
| `golden_answer_present` | yes / no / n/a |
| `notes` | free text |

---

## 4. Decision rule

- **Trafilatura passes all** → D42 confirmed.
10. **Throughput fails** → fallback resiliparse for text + separate metadata (trafilatura or meta/JSON-LD).
10. **Quality fails** → investigate config; if still fails → fallback.
10. **Readability** → optional, not a candidate.

---

## 5. Run record (template)

```json
{
  "run_id": "b-YYYYMMDDTHHMMSSZ",
  "thresholds_sha256": "<hash of this file>",
  "corpus": {"crawl": "CC-MAIN-2026-43", "warc_paths_sha256": "...", "sample": "T0"},
  "sample": {"en": 8000, "fr": 2000, "manual_en": 50, "manual_fr": 50, "seed": 0},
  "extractors": {
    "trafilatura": {"version": "...", "config": "..."},
    "resiliparse": {"version": "...", "config": "..."}
  },
  "tokenizers": [{"id": "...", "version": "..."}],
  "canon": "canon-v1",
  "chunker_skeleton_version": "...",
  "machine": {"gpu": "RTX Pro 6000", "vram_gb": 96, "ram_gb": 128, "vcpus": 16, "disk": "500 GB NVMe ephemeral"},
  "date": "2026-11-25T...Z",
  "outputs": "experiments/b-.../"
}
```

---

## 6. Hash

`4c9804f7d55ad6ca6b23f93664875d610544829398bb47b3f65073d55807eeee` — sha256 of the frozen thresholds content before this line.