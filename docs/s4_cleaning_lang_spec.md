# S4 — Cleaning & Language Detection Spec (D76 / D77)

**Status:** spec (planning). No code before the S4–S9 planning is complete (D47).
**Depends on:** D42 extractor (trafilatura), D43 canon-v1, D29 document schema.
**Frozen by:** this spec + the manifest (D79) records the versions.

---

## 1. Language detection (D76)

- **Tool (D76, follows D57):** **default GlotLID** (verify license at the pinned revision, believed Apache-2.0); fastText `lid.176` (CC BY-SA 3.0) only if an explicit decision extends D57 to tool models.
- **Granularity:** **document-level**, on `text_canonical` (after cleaning, §2).
- **Confidence threshold:** `TBD-B` (freeze before the run). Below threshold → `lang = "und"`.
- **Output:** `lang` field in the document metadata (D29); BCP-47 tag; `und` when undetermined.
- **Role:** gates the **80/20 T1 split** (D37), the D58 multilingual stats, and the B stratification.
- **Determinism:** same `text_canonical` + same detector version → same `lang` (bit-exact; recorded in the manifest, D79).
- **Tests:** EN/FR fixtures + short/ambiguous docs → `und`; code-switched docs → dominant language or `und` per threshold.

---

## 2. Cleaning pipeline (D77)

Order is fixed; each step is versioned and recorded in the manifest (D79).

| # | Step | Rule | Version key |
|---|---|---|---|
| 1 | **Boilerplate removal** | trafilatura output is the main text (D42); drop nav/footer/boilerplate. | extractor version |
| 2 | **NFC normalization** | Unicode NFC on the whole text; offsets are then computed on the NFC form (D78). | `nfc_version` (Unicode version) |
| 3 | **Control-char removal** | strip C0/C1 controls except `\n`, `\t`; keep `\n\n` paragraph breaks. | `cleaning_version` |
| 4 | **Min length** | doc shorter than `min_doc_chars` (`TBD-B`) → excluded with a reason code. | `cleaning_version` |
| 5 | **Exact dedup** | hash of `text_canonical`; one representative indexed; others `dup_of` + `not_in_index` (D50). | `dedup_version` |
| 6 | **Near-dedup** | **Disabled by default in v1** (D77); measure the near-dup rate on T0 (Jaccard ≥ 0.8 on 5-grams); enable only if rate > `X`%; if enabled, `dup_of` + `not_in_index` (D20). | `minhash_version` + threshold |

- **No language filtering here** — language is detected (§1), not used to drop; the 80/20 split is a sampling decision (D37), not a cleaning filter.
- **Quality/spam:** out of scope for v1 cleaning (no classifier, D41); revisit with `category` (D70 → 400).
- **Idempotence:** cleaning is deterministic; same input + same versions → same output (bit-exact).
- **Tests:** control chars, NFC on accents, min-length boundary, exact + near-dedup, `dup_of` chains.

---

## 3. What this unblocks

- **B protocol** can run on cleaned, language-tagged T0 (stratified EN/FR).
- **`r` (passages/doc)** and **tokens/word** measured on the final text form.
- **Manifest v1** (D79) records `cleaning_version`, `nfc_version`, `dedup_version`, `minhash_version`, lang-detector version.