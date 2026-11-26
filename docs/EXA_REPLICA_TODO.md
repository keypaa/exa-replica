# Exa Replica — Definition TODO

**Status key:** `[BLOCKER]` blocks **v1** · `[V1]` in v1 but not a design blocker · `[LATER]` out of v1, designed for.
**Rules:** measure before change/decide · one knob at a time · scale-invariance · idempotence · reproducibility.
**Detail:** `docs/EXA_REPLICA_RESEARCH.md` (§1.3 interfaces, §2 points, §3 research, §7 questions).

---

## Current focus

- [x] **S1** — protocol defined (Gates 0–5 + anti-goals); evidence pending
- [x] **S2** — contract matrix v1.0-gate0 frozen + v1.1; **0 blocker**
- [x] **S3** — reference box/corpus + tiers + storage; **0 blocker**
- [x] **S4** — planning complete; **D44 frozen 2026-11-26** (Run B, RTX) — passage spec settled
- [x] **S5** — planning complete (D57–D69, D81); model choice = D81 execution (evidence)
- [x] **S6** — planning complete (D82–D88); measurements pending
- [x] **S7** — planning complete (D89–D92); D89 amended 2026-11-26, only version pinning (M0)
- [x] **S8** — planning complete (D93/D94 + refs); evidence pending (snapshot/export/instrument)
- [x] **S9** — planning complete (D95–D98); D89 amended 2026-11-26, only version pinning (M0)
- [ ] **Baseline** — run the existing repo's tests/measurements and record what is reproducible (no new product code; eval harness allowed)

**Order (D80):** S5+S6 together; D81 depends on D73. **Cross-cutting done (D99–D103, D17 amended).**
**Evidence (in progress):** ✅ M0 preconditions (MCP SDK = MIT, spec 2025-11-25 current) + OpenAPI 2.0.0 captured (`docs/contracts/`) + `tools/list` captured. ⏳ Blocked on RTX/Modal + buckets (D39): run B (→ freeze D44), D81 execution, baseline build/measurements (§5). Then implementation M0→M5 (D97).

---

## Done

- [x] Research pass: Exa architecture, API/MCP surface, WET/WARC/WAT, embeddings, ANN, hardware, hybrid, LLM serving, licensing
- [x] Living research doc + candidate data structures + baseline
- [x] 17 points + data follow-ups + keep/cut + API-first
- [x] Interfaces v2.2 sketch + verification contract (`docs/sketches/v1_interfaces.py`)
- [x] Development rules (v1 + review additions)
- [x] Captured keyless Exa MCP `tools/list` + `web_search_exa` / `web_fetch_exa` schemas + response formats (2026-11-23)
- [x] Contract fixtures + curated 4-topic seed saved in `docs/fixtures/exa-mcp/` (tagged `curated`, not golden)
- [x] Trace record schema defined for capturing real `web_search_exa` calls
- [x] Mined OpenCode DB: 205 `websearch` calls / 179 unique; 0 with objective; topic skew measured
- [x] Read Exa blog (35 sources) → `docs/research/exa-blog-digest.md` (484 lines, tagged [S]/[I]/[?])
- [x] Tier-stratified query plan (30 queries, 10 domains) at `docs/fixtures/exa-mcp/query_plan.jsonl`
- [x] Captured 30-query Exa baseline (0 errors): lite p50 196 ms / auto p50 1.06 s / deep p50 7.84 s; summary in `docs/fixtures/exa-mcp/snapshots/`

---

## 17-point map (9 subjects + 8 blindspots + B1a/B1b/K1/A1)

| Point | Folds into | Where it lives |
|-------|------------|----------------|
| B1 Content acquisition reality | S4 | S4 |
| B2 Retrieval completeness | S6 | S6 |
| B3 Update / freshness lifecycle | S4/S6 | S4, S6 |
| B4 Answer / deep LLM | S5 | S5 |
| B5 Failure / degradation | S7 | S7 |
| B6 Caching / cost | S3/S7 | S3, S7 |
| B7 Evaluation at scale | S8 | S8 |
| B8 Ops / versioning / licensing | S9/S7 | S9, S7 |
| B1a WET metadata discarded | S4 | S4 |
| B1b WET lacks title/links/headers | S4 | S4 |
| K1 Keep/cut inventory | X | X |
| A1 API-first | S2/S7 | S2, S7 |

So the 9 subject rows below are the **workstreams**; the 8 blindspots (plus B1a/B1b/K1/A1) are **tracked inside them**.

---

## S1 — Definition of done (protocol defined; evidence open)

- [x] `[BLOCKER]` Gate 0 — core API: `/search` (lite+auto) + `/contents` on a real toy index, `/search`→`/contents` path, 400 on both routes, no MCP startup (D12) — *protocol frozen; evidence pending*
- [x] `[BLOCKER]` Gate 1 — drop-in: **our replica** MCP surface (2 tools, exact schemas, `Title/URL/Published/Author/Highlights`) (D8/§3.3.1) — *protocol frozen; replica evidence pending*
- [x] `[BLOCKER]` Gate 2 — behavior: v1 = keyless MCP + API exactly; plus keyed mode (2a–2f complete: surface, keys, limits, accounts/bans, DB, errors)
  - [x] `[BLOCKER]` 2a Surface & semantics — D8: MCP 2 tools + HTTP `/search` (lite/auto, contents text/highlights, filters) + `/contents`; keyless allowed
  - [x] `[BLOCKER]` 2b Key lifecycle — 2b.1 generation & storage (D3: hex secret, HMAC pepper, hash_version, fixed-length, uniform failure)
  - [x] `[BLOCKER]` 2b.2 Scopes — D4: v1 explicit scopes (`search:lite`/`search:auto`/`contents:read`), no hierarchy, route-level check, `StrEnum`; CLI local (no admin scope)
  - [x] `[BLOCKER]` 2b.3 Expiration — D5: 1-year default, `--no-expiry`, auth checks `expires_at`, UTC, injected clock, 14-day CLI warning
  - [x] `[BLOCKER]` 2b.4 Rotation — D6: 24h grace default (max 7d), refuse during grace, `rotated_from` no cascade, audit both ids, pepper version counter
  - [x] `[BLOCKER]` 2b.5 Revocation — D7: mandatory enum reason, idempotent, cache TTL + invalidation, bulk `--yes`/`--dry-run`, ban blocks key creation, never reactivates
  - [x] `[BLOCKER]` 2c Rate limits & quotas — D9: token bucket + daily counter, keyless 3 QPS/150/day, keyed 10/5/100 QPS, separate buckets, 429 vs 503
  - [x] `[BLOCKER]` 2d User management & bans — D10: suspend blocks usage+creation (reversible), ban revokes+blocks (no expiry), both checked at auth + cache invalidation, shared reason enum
  - [x] `[BLOCKER]` 2e DB schema — Postgres v1 (§4.5); storage ports `DocumentStore`/`PassageStore` in `ports/` (D95); Postgres adapter in `adapters/outbound/store/`; testcontainers
  - [x] `[BLOCKER]` 2f Error semantics — D11: Exa envelope + X-Request-Id, strict auth order, 429/503 + Retry-After, MCP JSON-RPC vs isError, custom tags marked
- [x] `[BLOCKER]` Gate 3 — quality — *protocol frozen (D14/D93/§1.5); evidence pending; Exa snapshot blocked (D19)*
  - [x] `[BLOCKER]` 3a Golden set — resolved (planning) → **D93** (§1.5; EN gate 100/100, FR diagnostic 100); *evidence pending*
  - [x] `[BLOCKER]` 3b Judge calibration — resolved (planning) → **§1.5 + D14** (blind, κ≥0.6 provisional); *evidence pending*
  - [ ] `[LATER]` 3c Exa snapshot — blocked (ToS §4.2(f), D19); replica vs BM25; private durable storage
  - [x] `[BLOCKER]` 3d ANN operating point — D13 (nprobe sweep **replaced by D82**; history kept)
  - [x] `[BLOCKER]` 3e Quantization — D13: three lists F/Q/A; `Q vs F` quantization, `A vs Q` index, `A vs F` delivered; gaps don't add; binary vs float first
  - [x] `[BLOCKER]` 3f Coverage — D13: URL / evidence / indexed passage, same denominator, loss breakdown, no search-engine path
  - [x] `[BLOCKER]` 3g Ranking quality — D14: paired auto−Exa (two-sided 95% CI, δ=0.05 candidate), auto−BM25 relative floor, success@3 diagnostic, judged@10=100%
  - [x] `[BLOCKER]` 3h Quality gate scope — D14: auto = non-inferiority Exa + superiority BM25; lite reported + BM25-floored (explicit margin); filters HTTP-only
  - [x] `[BLOCKER]` 3i Objective ablation — D14: primary query+objective vs BM25 query-only; 3 Exa conditions on dev; judge objective constant
  - [x] `[BLOCKER]` 3j Judgment versioning — freeze outputs, recompute all scores per version, pool extension vs new protocol vs new benchmark, task+reference-objective keys, 100% judged@10 for gate, hashed export
- [x] `[BLOCKER]` Gate 4 — performance — *protocol frozen (D15/D16); evidence pending*
  - [x] `[BLOCKER]` 4a Latency — D15: lite/auto pilot targets (p50/p95/p99), p90 reported not gated, end-to-end `/search` primary + `/contents`/MCP complementary
  - [x] `[BLOCKER]` 4b Throughput — D15: useful responses, open arrival rate, error budget, capacity vs quota, per-tier isolation
  - [x] `[BLOCKER]` 4c Resources — D15: one reference box + corpus (docs+passages), VRAM idle/startup/peak, aggregate GPU-seconds, memory margin in GiB
  - [x] `[BLOCKER]` 4d Load test methodology — D16: k6 constant-arrival-rate, 10-min plateau + drain, isolated/mixed/saturation→recovery/cold, per-route offered load, planned/sent/successful, frozen profile, time series
- [x] `[BLOCKER]` Gate 5 — scale & ops (D17: v1 ops vs L5 scale)
  - [x] `[BLOCKER]` 5a Scale invariance — same code/contracts; shard/replica/node/GPU distinct; Test A (1 vs N shards) + Test B (growing corpus); page-id partition; per-branch merge
  - [x] `[BLOCKER]` 5b Byte-exact — canonical artifact manifest vs run manifest; declared profile; idempotence key; resume after mid-write/pre-activation
  - [x] `[BLOCKER]` 5c Provenance — reconstruct index / recompute scores / replay perf; another person from the manifest; inaccessible → not reconstructible
  - [x] `[BLOCKER]` 5d Observability — OTel + metrics + JSON logs; duration/result/volumes/decision; no PII/content; collector down ≠ service down
  - [x] `[BLOCKER]` 5e CI/CD — digest-promoted artifacts; trusted-code GPU tests; RC evidence; rollback binary+index+schema
  - [x] `[BLOCKER]` 5f Failure semantics — no partial success; queue full 503; OOM supervisor; manifest/quarantine; shard failover same version; 504 gateway; recovery vs durable data
- [x] `[BLOCKER]` Confirm L0–L5 and the v1 target (D1: v1 architecture L0–L2; releasable L0–L2 + L3 + L4; L5 scale proof)
- [x] `[BLOCKER]` Anti-goals — integrity, security, promised compatibility, reproducibility, v1 recovery, idempotence, no gate shortcuts, no unauthorized data, no failure-as-success
- [x] (folded into 3a) Golden set: 200 queries (100 dev + 100 test), provenance-tagged, frozen
- [x] (folded into 3c) Exa snapshot: date, exact params, raw responses, fetched text; ToS check
- [x] (folded into 3b) Judge calibration: frozen config, blind, 50–100 hand labels, Cohen's κ
- [x] `[BLOCKER]` Exa comparison blocked by ToS; a release may publish without a parity claim → **D18/D19**

## S2 — Product contract

- [x] `[BLOCKER]` **S2 v1.0-gate0 frozen** → `docs/s2_contract_matrix.md` (sha256 `c2920819…595c43`)
- [x] `[BLOCKER]` Confirm v1 scope: `/search` (lite, auto) + `/contents` (text, highlights); MCP `web_search_exa` + `web_fetch_exa`
- [x] `[BLOCKER]` Contract matrix drafted → `docs/s2_contract_matrix.md`
- [x] `[BLOCKER]` Later fields (summary, extras, maxAgeHours, snapshotAsOf, livecrawl, subpages, outputSchema, stream) → 400 `unsupported_field` (D27)
- [x] `[BLOCKER]` Filter × `type` table before Gate 1 (D70: lite=auto filters; category→400; S2 v1.1)
- [x] `[BLOCKER]` `/contents` per-item status shape (D20; s2 §8 CHOICE `ok|not_found|not_in_index`)
- [x] `[BLOCKER]` MCP bounds (`web_fetch_exa.urls` 1–100, string 1–2048; s2 §8)
- [x] `[BLOCKER]` `maxCharacters` 1M vs 5M (s2 §8 DOC)
- [x] `[BLOCKER]` MCP wire compatibility: match the keyless tool schemas + `Title/URL/Published/Author/Highlights` text format; HTTP is semantic. Observed one session; error/auth/stdio fixtures still needed
- [x] `[BLOCKER]` Resolve MCP vs HTTP split (D8/D26/D27): MCP fixed `auto`, no filters; HTTP `lite`/`auto` + filters; `objective` consumed; `deep`→400
- [x] `[BLOCKER]` Tier selection (D8/D27): MCP fixed `auto`; HTTP explicit `type`; classifier later
- [x] `[BLOCKER]` Capture error/auth/stdio fixtures (D71 rule; collection = Gate 1 prerequisite)
- [x] `[BLOCKER]` Error envelope (D11): Exa `{requestId, error, tag}`
- [x] `[BLOCKER]` Auth (D24): `x-api-key` + Bearer; keyless by config; MCP OAuth LATER
- [x] `[BLOCKER]` Versioning (D25): no `/v1` prefix; contract version + header
- [x] `[BLOCKER]` S2 v1.1 (D67/D69): normalized `score` + `degraded` field (backward-compatible; Gate 0 hash unchanged)
- [ ] `[LATER]` `/answer`, `/findSimilar`, `/context`, Agent, Monitors, Websets, deep tiers (contracts in §3.11)
- [ ] `[LATER]` SSE streaming for `outputSchema`

## S3 — Scale envelope & hardware

- [x] `[BLOCKER]` Corpus source: Common Crawl WARC (D28)
- [x] `[BLOCKER]` Language: English primary + French secondary tagged (D33)
- [x] `[BLOCKER]` Reference hardware profile: RTX Pro 6000 96 GB / 128 GB RAM / 16 vCPU (D34/D36)
- [x] `[BLOCKER]` Measurement exception: WARC acquisition + T0/T1 ingest allowed (D35)
- [x] `[BLOCKER]` D35 parameters: CC-MAIN-2026-43, ≤500 GB, retention rules, T2+ new decision, Modal off T0/T1 (D35)
- [x] `[BLOCKER]` Disk capacity/type: 500 GB NVMe (D36); open S6 question = IOPS if ANN read from disk
- [x] `[BLOCKER]` EN/FR ratio: 80/20 (D37)
- [x] `[BLOCKER]` Corpus cache & reuse (D38/D40): HF buckets `exa-replica-corpus` + `exa-replica-artifacts`, manifests repo, no re-download
- [x] `[BLOCKER]` HF bucket provisioning + quota guard (≤2.5 TB; T0/T1 ≤500 GB; fail before download if over) (D38)
- [x] `[BLOCKER]` Modal persistent <1 TB; working-only; sync back to HF (D38)
- [x] `[BLOCKER]` Execution locality (D39): RTX/Modal only; Thinkpad never builds
- [x] `[BLOCKER]` T2 raw WARC: stream to scratch, delete, not stored in HF (D40)
- [x] `[BLOCKER]` Measure rebuild time from cache (D74: keep text+passages, drop WARC; rebuild ≤12 h)
- [x] `[BLOCKER]` Document/passage definition + passage ratio measured (D29; `r` measured in B)
- [x] `[BLOCKER]` Nested tiers T0–T2 + deterministic permutation (D30)
- [x] `[BLOCKER]` Coverage per tier + no injection; absolute threshold per tier (D31)
- [x] `[BLOCKER]` Artifact reuse: diff(ideal, actual), global stages versioned, idempotence key excludes resources, tolerance, GC (D32)
- [x] `[BLOCKER]` Target corpus sizes (T0 ~10k / T1 ~1M / T2 ~10–25M) (D30)
- [x] `[BLOCKER]` Hardware classes: v1 pinned to D36; 5090/B300/H200 = new profile + decision (D36/D62)
- [x] `[BLOCKER]` Per-tier latency budgets (p50/p95) and throughput (QPS) (D15/D16/D66)
- [x] `[BLOCKER]` Exa latency baseline per tier (n=10): lite p50 196 ms, auto 1.06 s, deep 7.84 s — reference, not target
- [x] `[BLOCKER]` Memory policy (D72): serving ≤96 GB, build peak ≤120 GB; else quantize/disk index (S6)
- [x] `[BLOCKER]` Single-node vs multi-node for v1 (D36 single box; multi-GPU LATER, D68)
- [x] `[BLOCKER]` Storage budget → head of S6 (D73: T1×2 + temp + 15% ≤ 500 GB)
- [x] `[BLOCKER]` Scale test methodology (D75: 10k/100k/1M, ±20% extrapolation)
- [x] `[BLOCKER]` Modal behind an execution interface; rebuild without Modal must work (D38/D39)
- [ ] `[LATER]` Cost model ($/query, GPU-hours)

## S4 — Data plane

- [x] `[BLOCKER]` Acquisition: **CC-MAIN-2026-43**, columnar index + WARC range requests (D28)
- [ ] `[LATER]` Vertical indexes (people, companies, products, places, code, publications) — v1 = general web only; verticals arrive with `category` (D70 → 400)
- [ ] `[LATER]` Snapshot / time-travel versioning — v1 = single crawl (CC-MAIN-2026-43), `generation_id` in manifest, updates via rebuild only
- [x] `[BLOCKER]` Non-negotiable fields: title, url, publishedDate, author, text, highlights, links, categories, language (D29, §4.1.1)
- [x] `[BLOCKER]` Identity: `doc_id` = (generation, url_canonical); `content_hash` attribute (D18/D20/D29)
- [x] `[BLOCKER]` Generation vs build: `generation` = corpus; `build_id` = build manifest hash; serving points to build (D45)
- [x] `[BLOCKER]` Manifest schemas v0 drafted (`docs/s4_manifest_schemas_v0.md`, D46): corpus / build spec+result / artifact / run record
- [x] `[BLOCKER]` Manifest v1 fields frozen (D79: generation_id, WARC-list hash, versions, model, PromptConfig, precision, counts, licenses)
- [x] `[BLOCKER]` Minimal document schema (D41, §4.1.1)
- [x] `[BLOCKER]` Passage spec (chunking): **frozen as D44 2026-11-26** (Run B: target 128 / max 192 words, overlap 1; tokens/word 2.4755) — `docs/s4_passage_spec_skeleton.md`, `docs/research/t0-tokens-report.md`
- [x] `[BLOCKER]` Tokenizer: model tokenizer is a constraint only; `chunker_version` = UAX #29 words (D60)
- [x] `[BLOCKER]` B protocol: tokens/word + overflow written (`docs/s4_b_tokens_protocol.md`)
- [x] `[BLOCKER]` B thresholds frozen (`docs/s4_b_thresholds.md`, sha256 `4c9804f7…eeee`) + run_record template
- [x] `[BLOCKER]` B prerequisites: list written (`docs/s4_b_tokens_protocol.md` §1)
- [x] `[BLOCKER]` Extractor: trafilatura, version/config frozen (D42, §4.1.3)
- [x] `[BLOCKER]` URL canonicalization: canon-v1, shared pipeline/API (D43, §4.1.3)
- [x] `[BLOCKER]` UTF-8 byte offsets on NFC text; no offsets exposed in API v1; convert at highlights output (D78)
- [x] `[BLOCKER]` Dedup: exact by content_hash; one representative indexed; `dup_of` + `not_in_index` (D50)
- [x] `[BLOCKER]` Language detection: **GlotLID (D76)**, doc-level, threshold, `und` (D76, `docs/s4_cleaning_lang_spec.md`)
- [x] `[BLOCKER]` Exclusion table (takedown/PII/opt-out) at build + serving (D52)
- [x] `[BLOCKER]` Cleaning: boilerplate → NFC → control chars → min length → exact dedup → near-dedup (MinHash), versioned (D77, `docs/s4_cleaning_lang_spec.md`)
- [x] `[BLOCKER]` Content store: two forms (build columnar + derived docstore), passages offsets-only, sharding hash(url) mod N (D48/D49)
- [x] `[BLOCKER]` Content-store decision rules: Parquet default, zstd, dedup, N formula (D50)
- [x] `[BLOCKER]` S4 step 6: incremental/freshness — v1 full rebuild per build/generation (D56)
- [x] `[BLOCKER]` S4 step 7: content policy D51 (full/excerpt/none; v1 internal full)
- [x] `[BLOCKER]` Takedown procedure (D52)
- [x] `[BLOCKER]` Retention (D53)
- [x] `[BLOCKER]` Licenses: code Apache 2.0; models Apache/MIT; data CC ToS (D55)
- [x] `[BLOCKER]` PII: exclusion now; detection later (D54)
- [x] `[BLOCKER]` S4 step 8: live fetch (later, seam) (D56)
- [x] `[BLOCKER]` B1a/B1b classified in S4 (D56)
- [x] `[BLOCKER]` S4 steps 1–8 + B1a/B1b classified; **planning complete** — only the passage spec (D44) awaits the B measurement
- [x] `[BLOCKER]` Update/freshness: v1 full rebuild per generation; deletes via exclusions; robots/noindex; `maxAgeHours` LATER (D56)
- [x] `[BLOCKER]` Licensing/PII: store, retention, takedowns (D52/D53/D54/D55)
- [ ] `[V1]` B1a: read `warc-date` + `warc-identified-content-language`
- [ ] `[V1]` B1b: WAT/WARC for title, links, headers
- [x] `[BLOCKER]` Provenance/manifest schema v0 (D46); v1 frozen before first T1 build (tracked above)
- [ ] `[LATER]` Live fetch (seam, D56) — reopen SSRF (D91/12)

## S5 — Models

> Items tagged `[BLOCKER]` that are **measurements** are `[EVIDENCE]` (block v1, not planning gaps).

- [x] `[BLOCKER]` Embedding model choice: rule + eval protocol → **D81**
- [x] `[BLOCKER]` Model provenance in manifest → covered by D57 (fields) + D79 (inclusion)
- [ ] `[BLOCKER]` D81 steps 0–1: long list (≤1B params, dated MTEB capture per D71) + license/language filters on model cards
- [ ] `[BLOCKER]` D81 filters 3–4: throughput (10k T0 passages, bf16, batch 32/64/128/256) + query p95 on D36 — depends on D44
- [ ] `[BLOCKER]` D81 filter 5: vector size vs D73 "vectors" share — depends on D73
- [ ] `[BLOCKER]` D81 dev pilot: σ of paired diffs (BM25 vs hybrid of 1st admitted) — depends on dev golden set; **if no golden set → provisional choice (labelled, cannot be frozen)**
- [ ] `[BLOCKER]` D81 full finalist run + bootstrap → D81-R; write model/version/PromptConfig/precision into spec (D79)
- _Moved:_ embedding cache → S7; highlights model → S6 (check S8 duplicate); Rust LUT bench → S6
- [x] `[BLOCKER]` Licensing D57 (Apache/MIT; verify per revision)
- [x] `[BLOCKER]` Multilingual D58 (one model + EN reference)
- [x] `[BLOCKER]` Single-vector D59 (multi LATER)
- [x] `[BLOCKER]` PromptConfig D61
- [x] `[BLOCKER]` Weight precision D62 (bf16 default, fp8 conditional)
- [x] `[BLOCKER]` Determinism D63
- [x] `[BLOCKER]` Serving/batching/throughput D64
- [x] `[BLOCKER]` Build budget T1 D65
- [x] `[BLOCKER]` Latency split D66
- [x] `[BLOCKER]` Reranker D67
- [x] `[BLOCKER]` GPU sharing D68
- [x] `[BLOCKER]` Tokenizer/max tokens D60 (model-independent unit; model tokenizer constraint)
- [x] `[BLOCKER]` Long docs → S4 chunker (D60)
- [x] `[BLOCKER]` Model fallback / BM25-only D69
- [x] `[BLOCKER]` Hardware mapping D36/D62
- [ ] `[LATER]` Generator (local/pluggable, citations)

## S6 — Index & retrieval

> Items tagged `[BLOCKER]` that are **measurements** are `[EVIDENCE]` (block v1, not planning gaps).

- [x] `[BLOCKER]` Disk budget → D73 (caps F/L/G/V/S, 15% reserve, build cycle, pre-build check, 85% emergency stop)
- [ ] `[BLOCKER]` Measure `C_util` on D36 (`df`, Gio) → record in run manifest
- [ ] `[BLOCKER]` D73: bytes/doc per component at 10k/100k → T1 projection ×1.2; ±20% check at 1M (D75)
- [ ] `[V1]` Pre-build check + 85% emergency stop → specify in the build runbook (M3/M5)
- [ ] `[V1]` Disk alerts 75% / 85% (M5)
- [x] `[BLOCKER]` Index settings candidates → **D82** (R0 exact GPU default, R1 binary + int8 rescoring fallback; MRL/HNSW/PQ excluded v1)
- [ ] `[BLOCKER]` D82: measure R0 (p95 latency, VRAM) on D36 — depends on D81 model, D44 N_passages
- [ ] `[BLOCKER]` D82: measure R1 (latency, RAM, recall@100 vs R0, K_bin sweep) + nDCG loss for D81 step 4
- [ ] `[BLOCKER]` D82/D68: confirm whether build and serving share the GPU
- [ ] `[V1]` Runbook: generation switch in VRAM (2×V_gpu peak or short dense outage, BM25 still served) (M5)
- [x] `[BLOCKER]` BM25 index settings → **D83** (Tantivy default, passages unit, EN/FR two-field, k1=1.2/b=0.75, no positions, safe query parsing)
- [ ] `[BLOCKER]` D83: measure BM25 p95 (50/80 ms D66), RAM (D72), index size G (D73), build time (D65) on D36
- [ ] `[BLOCKER]` D83: verify Tantivy license at pinned revision (fallback Lucene) + tantivy-py vs JVM
- [ ] `[BLOCKER]` D83: A vs B analysis on FR dev (paired IC95) → keep A (two-field Snowball) or B (neutral)
- [x] `[BLOCKER]` Index family → **D82** (R0 exact GPU default; R1 binary+int8 fallback; custom/FAISS/HNSW/PQ excluded v1)
- [x] `[BLOCKER]` Index interface → **D85** (`DenseIndex`/`LexicalIndex`: search/stats/version; no add/delete v1; `UnsupportedFilter`)
- [x] `[BLOCKER]` DAG/plan orchestrator → **D86** (static `TierPlan` v1, D66 order, deadline, trace; Canon DAG LATER; workers → S7)
- [x] `[BLOCKER]` Sharding/rebalancing; multi-GPU → **D87** (1 local shard/branch v1; N partitions for 5a; per-branch merge before RRF; BM25 global stats; rebalancing/multi-GPU LATER)
- [x] `[BLOCKER]` Recall target per tier → **D88** (R0=1, R1≥0.95@100; same lite/auto; D14/D19)
- [x] `[BLOCKER]` Binary vs PQ vs float; dims → **D82** (dims = D81 model; MRL/PQ excluded)
- [x] `[BLOCKER]` IVF k/nprobe → **replaced by D82** (R0/R1 scan the whole index, no IVF)
- [x] `[BLOCKER]` Hybrid: BM25 + dense, RRF k=60 → **D81/D83** (SPLADE later)
- [x] `[BLOCKER]` Hybrid BM25 + dense is **v1** (acté)
- [x] `[BLOCKER]` Highlights extractive v1 → **D84** (query-time sentences, reference passage, D51 directives, R1 S0/S1, R2 latency, R3 count/length)
- [ ] `[BLOCKER]` D84: measure highlight metric **D94** + added p95 (R2) on D81 (dev split = 100 EN dev + 100 FR diagnostic)
- [ ] `[BLOCKER]` D84: R1 S0 vs S1 (adopt S1 only if gain ≥2 pts IC95>0 and latency ≤ R2; lite forces S0)
- [ ] `[V1]` D84: fix no-punctuation window N chars + default 1 excerpt/≤3 sentences (names/bounds **S2 D8/D27**; options need S2 v1.1 if only `highlights: true`) (M4)
- [ ] `[LATER]` Dynamic highlights (LLM, cross-result; the v1 extractive is D84)
- [x] `[BLOCKER]` Passage vs document index → **D83/2** (passages; doc = max; winning passage kept, correction A)
- [x] `[BLOCKER]` Filters pre/post → **D70 + D83/6** (before fusion; roaring; domain/date/category)
- [x] `[BLOCKER]` Benchmark the Rust LUT hot loop vs Exa's C++ note → **[RESOLVED→D82]** (IVF/LUT excluded; R0/R1 exact)
- [ ] `[LATER]` Kernels/assembly beyond the current LUT

## S7 — Serving & platform

**Reference table (decided elsewhere — do not re-decide):**
| Subject | Decision |
|---|---|
| Auth, keys, quotas, 429/503 | D3–D11, D24 |
| Errors, `X-Request-Id`, correlation IDs | D11 |
| MCP transports (stdio/HTTP), schemas | D8, D22, D23 |
| Concurrency (async I/O only, `Deadline`, bounded queues, 503≠504, pool isolation, `index_version`, job context) | §1.3.1 |
| Degradation / `degraded` | D69, §1.3.1 |
| Observability (OTel + metrics + JSON logs) | D17 5d |
| CI/CD (digest-promoted) | D17 5e |
| Failure semantics (no partial success, 503 queue full, OOM supervisor) | D17 5f, §1.3.1 |
| Versioning API / index / model / manifest | D25, D45, D46, D79 |

- [x] `[BLOCKER]` HTTP/MCP framework + topology → **D89** (gateway + workers; FastAPI/Starlette + MCP SDK)
- [x] D89 : licence SDK Python = MIT (vérifié 2026-11-26)
- [ ] `[BLOCKER]` D89 : nouvelle cible 2026-07-28 + SDK 2.x ; revue des docs (`initialize`, sessions, `Mcp-Session-Id`, exemples v1/FastMCP)
- [ ] `[V1]` (M0) D89 : figer les versions FastAPI + mcp 2.x
- [x] `[BLOCKER]` MCP transport (stdio + HTTP); tool schemas → D22/D23
- [x] `[BLOCKER]` Auth; rate limits; 429/503 → D3–D11, D24
- [x] `[BLOCKER]` Concurrency → §1.3.1 (pools, deadline, bounded queues, isolation)
- [x] `[BLOCKER]` Caching → **D90** (embedding + contents; LRU RAM; cold-cache gate)
- [x] `[BLOCKER]` Degradation → D69, §1.3.1
- [x] `[BLOCKER]` Observability → D17 5d
- [x] `[BLOCKER]` Security concrete → **D91** (HMAC keys/prefix-only logs, TLS proxy, size limits, 413, CORS off, secrets, redaction, no eval/exec/pickle, path containment, IPC 0600, SSRF out of v1)
- [x] `[BLOCKER]` CI/CD; deployment → D17 5e
- [x] `[BLOCKER]` Config/DI → **D92** (pydantic-settings, composition root per process, startup manifest check)
- [x] `[BLOCKER]` Failure semantics → D17 5f, §1.3.1
- [x] `[BLOCKER]` Versioning → D25, D45, D46, D79
- [x] `[BLOCKER]` Correlation IDs → D11

## S8 — Evaluation & benchmarking

**Reference table (decided elsewhere — do not re-decide):**
| Subject | Decision |
|---|---|
| ANN recall vs exact (R0=1, R1≥0.95@100) | D13 3d/3e, D82, D88 |
| Quantization recall (lists F/Q/A) | D13 3e, D82 |
| Coverage (judged-relevant ∩ indexed) | D13 3f |
| Judge calibration, judged@k, versioning | §1.5 (Judge calibration, Judgment versioning) + D14 |
| Test split 1×/RC, constants on dev | §1.5 + D14/D81 |
| Pilot σ on dev | §1.5, D81 |
| Per-query objective (specific primary) | D14, D33 |
| Judgments keyed URL + content_hash | D18/D20/D29, D13 |
| Selection procedure, privacy, query source | §1.5 (Selection, Privacy) |
| BM25 floor (relative, bootstrap >0) | D14, D19 |
| Paired bootstrap CIs | D14, D81 |
| Metrics recall@k / MRR / nDCG | D13, D14 |
| Load testing | D16 (Gate 4) |
| Reproducibility (provenance, seeds) | D17 5b/5c, D32, D63 |
| Scale extrapolation (±20%) | D75 |
| Regression gates in CI | D17 5e |
| Fast bench harness | §1.5, D35 |
| Golden set | D93 |
| Highlight metric | D94 |
| Research/answer eval | `[LATER]` (reopen if `/answer` in scope) |

- [x] `[BLOCKER]` ANN recall vs exact → D13/D82/D88
- [x] `[BLOCKER]` Quantization recall → D13 3e/D82
- [x] `[BLOCKER]` Coverage → D13 3f
- [x] `[BLOCKER]` Golden set → **D93** (EN gate 100/100; FR diagnostic 100; growth rule)
- [x] `[BLOCKER]` Representative query set → **D93** (closed domain strata)
- [ ] `[LATER]` Exa snapshot + ToS → D19/D71 (blocked; evidence)
- [x] `[BLOCKER]` Judge calibration → §1.5 + D14
- [x] `[BLOCKER]` judged@k + incremental → D14
- [x] `[BLOCKER]` Judgment versioning → §1.5 + D14
- [x] `[BLOCKER]` Test split once/RC → §1.5 + D14/D81
- [x] `[BLOCKER]` Pilot SD on dev → §1.5/D81
- [x] `[BLOCKER]` Per-query objective → D14/D33
- [x] `[BLOCKER]` Judgments keyed URL+hash → D18/D20/D29
- [x] `[BLOCKER]` Selection procedure → §1.5
- [x] `[BLOCKER]` Privacy scrub → §1.5
- [x] `[BLOCKER]` Query source objective logs → §1.5/§3.12
- [x] `[BLOCKER]` Objective strategy → D14/D33
- [ ] `[V1]` Export deduped query set → evidence (privacy approval)
- [ ] `[V1]` Instrument tool to log `objective` → evidence/future
- [x] `[BLOCKER]` Coverage caveats → D13
- [x] `[BLOCKER]` BM25 floor → D14/D19
- [x] `[BLOCKER]` (a2) at candidate depth N → D13 3e / §1.5
- [x] `[BLOCKER]` Highlight relevance → **D94** (metric); model → S6/D84
- [ ] `[LATER]` WebCode/ATLAS-style evals
- [x] `[BLOCKER]` Paired bootstrap CIs → D14/D81
- [x] `[BLOCKER]` Metrics recall@k/MRR/nDCG → D13/D14
- [x] `[BLOCKER]` Load testing → D16
- [ ] `[LATER]` Research/answer eval (reopen if `/answer` in scope)
- [x] `[BLOCKER]` Reproducibility → D17 5b/5c/D32/D63
- [x] `[BLOCKER]` Scale extrapolation → D75
- [x] `[BLOCKER]` Regression gates in CI → D17 5e
- [x] `[BLOCKER]` Fast bench harness → §1.5/D35

## S9 — Repo & milestones

**Reference table (decided elsewhere — do not re-decide):**
| Subject | Decision |
|---|---|
| Repo, layout, naming, packaging | D95 |
| Dependency rules (import-linter) | D96 |
| Config/DI | D92 |
| CI/CD, release (digest-promoted) | D17 5e |
| Code / model / data licenses | D55 |
| Security (P1) | D91 |
| Observability (P2/P3) | D17 5d |
| Measurement harness exception | §1.5, D35 |

- [x] `[BLOCKER]` Package layout; Rust crate layout → **D95** (domain/ports/application/adapters/bootstrap/entrypoints + `ann-core`)
- [x] `[BLOCKER]` Dependency rules (`import-linter`) → **D96** (layer contract, down-only, blocking CI)
- [x] `[BLOCKER]` Config/DI wiring → **[RESOLVED→D92]**
- [x] `[BLOCKER]` Repo strategy → **D95** (new repo default; measure = reused-code share; harness migrated with history)
- [x] `[BLOCKER]` Naming → **D95** (`exa-replica` internal; public name neutral by D97; crate `ann-core` / module `ann_core`)
- [x] `[BLOCKER]` Milestones + smallest steps; DoD per milestone → **D97** (exit criteria tied to gates D18/D19/D31; public name here)
- [x] `[BLOCKER]` Licensing/CLA/DCO; docs; release/versioning → **D98** (DCO default; SemVer; docs); code/model/data → D55
- [ ] `[V1]` (M0) D89 : figer FastAPI + mcp 2.x (cible 2026-07-28) — prérequis M0

## Cross-cutting

- [x] `[BLOCKER]` P0 Agent governance → **D101** (`AGENTS.md` source, `CLAUDE.md` → pointer, CI check); pillars, anti-drift, DoD
- [x] `[BLOCKER]` P1 Security → **D91**
- [x] `[BLOCKER]` P2 Observability → **D17 5d** (per-pool metrics D89 added, amended)
- [x] `[BLOCKER]` P3 Resource observability → **D15 4c / D17 5d**
- [x] `[BLOCKER]` Confirm interfaces v2.2 decisions 1–5 → **D99**
- [x] `[BLOCKER]` Measurement-harness exception → **§1.5 / D35**
- [x] `[BLOCKER]` Confirm dev rules thresholds + enforcement → **D102**
- [x] `[BLOCKER]` Confirm keep/cut (K1) → **D100** (ann-core optional R1)
- [x] `[BLOCKER]` Confirm API-first (A1) → **D8/D12/§3.3.1**
- [x] `[BLOCKER]` Write `AGENTS.md` (source) + `CLAUDE.md` → `AGENTS.md` → **D101**
- [x] `[BLOCKER]` Fetch Exa OpenAPI + `tools/list` as contract artifacts → **D103** — OpenAPI 2.0.0 captured (`docs/contracts/exa-openapi-2.0.0.yaml` + PROVENANCE); `tools/list` already captured; ToS respected (no API calls)
- [x] `[BLOCKER]` Baseline protocol defined → **§5** (repo baseline; D19 = Exa parity)
- [ ] `[BLOCKER]` Baseline run (evidence) — `cargo test`/build on RTX (D39); read-only inventory on Thinkpad
