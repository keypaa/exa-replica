# S2 — Contract Matrix v1.0-gate0

**Frozen:** 2026-11-25 · **Status:** final — Gate-0 fields complete; later fields explicitly 400.
**Sources:** `DOC` = `exa-spec.yaml` (public spec 1.2.0, fetched 2026-11-24, sha256 recorded in git) · `CHOICE` = replica decision (D) · `NV` = unverified.
**No `OBS` rows:** the keyless observation is a frozen capture, not a citable spec. MCP rows are `DOC` (public MCP spec 2025-11-25) or `CHOICE`.

**Rules:**
- **Null:** `null` = absent for optional fields; `null` on a required field → 400.
- **Unsupported:** documented-but-not-implemented → **400 `unsupported_field`**; a field sent at its **default value** is accepted.
- **Gate 0:** every field tested by Gate 0 has a row; v1 fields not in Gate 0 are tested before release (Gate 1+).
- **MCP and HTTP call the same in-process `SearchService`.** Any other divergence is a bug.

---

## 1. HTTP `POST /search`

| Field | Type | Req | Default | Null | Bounds | Unsupported | Error | Source | Gate |
|---|---|---|---|---|---|---|---|---|---|
| `query` | string | yes | — | no | minLength 1 | — | 400 `invalid_request` | DOC | Gate 0 |
| `type` | enum | no | `auto` | no | `lite`\|`auto` | 400 `unsupported_value` (deep) | 400 | DOC/CHOICE D8 | Gate 0 |
| `numResults` | integer | no | 10 | no | 1–100 | — | 400 | DOC | Gate 0 |
| `includeDomains` | array | no | null | yes | ≤1200 | — | 400 | DOC | Gate 1 |
| `excludeDomains` | array | no | null | yes | ≤1200 | — | 400 | DOC | Gate 1 |
| `startPublishedDate` | date-time | no | null | yes | ISO 8601 | 400 `unsupported_field` | 400 | DOC | LATER |
| `endPublishedDate` | date-time | no | null | yes | ISO 8601 | 400 `unsupported_field` | 400 | DOC | LATER |
| `category` | string | no | null | yes | enum + hints | 400 `unsupported_field` | 400 | DOC | LATER |
| `contents` | object | no | null | yes | — | — | 400 | DOC | Gate 0 |
| `contents.text` | bool/object | no | false | yes | maxChars ≤1,000,000 | — | 400 | DOC | Gate 0 |
| `contents.highlights` | bool/object | no | false | yes | maxChars/query/dynamic | — | 400 | DOC | Gate 0 |
| `objective` | string | no | null | yes | 1–4096 | — | 400 | DOC | Gate 0 |
| `moderation` | bool | no | false | yes | — | 400 `unsupported_field` (true) | 400 | DOC | LATER |
| `userLocation` | string/object | no | null | yes | ISO country / lat-lon | 400 `unsupported_field` | 400 | DOC | LATER |
| `outputSchema` | object | no | null | yes | — | 400 `unsupported_field` | 400 | DOC | LATER |
| `additionalQueries` | array | no | null | yes | 1–10 | 400 `unsupported_field` | 400 | DOC | LATER |
| `stream` | bool | no | false | yes | — | 400 `unsupported_field` (true) | 400 | DOC | LATER |

**Notes:** `objective` optional on HTTP, required on MCP (CHOICE D26). `type` open in Exa; v1 rejects non-`lite`/`auto` with 400 (D8). Filters: one row per filter × `type` before Gate 1.

---

## 2. HTTP `POST /contents`

| Field | Type | Req | Default | Null | Bounds | Unsupported | Error | Source | Gate |
|---|---|---|---|---|---|---|---|---|---|
| `ids` | array | **XOR** | — | no | 1–100, string 1–2048 | — | 400 (both/none) | DOC/CHOICE D20 | Gate 0 |
| `urls` | array | **XOR** | — | no | 1–100, string 1–2048 | — | 400 (both/none) | DOC/CHOICE D20 | Gate 0 |
| `text` | bool/object | no | false | yes | maxChars ≤5,000,000 | — | 400 | DOC | Gate 0 |
| `highlights` | bool/object | no | false | yes | maxChars/query; incompatible with `dynamic` | — | 400 | DOC | Gate 0 |
| `summary` | object | no | null | yes | query/schema | 400 `unsupported_field` | 400 | DOC | LATER |
| `extras` | object | no | null | yes | links/images | 400 `unsupported_field` | 400 | DOC | LATER |
| `maxAgeHours` | int | no | null | yes | -1–720 | 400 `unsupported_field` | 400 | DOC | LATER |
| `snapshotAsOf` | date | no | null | yes | ISO | 400 `unsupported_field` | 400 | DOC | LATER |
| `livecrawl` | string | no | null | yes | never/always/fallback/preferred | 400 `unsupported_field` | 400 | DOC | LATER |
| `subpages` | int | no | 0 | yes | 0–100 | 400 `unsupported_field` | 400 | DOC | LATER |

**D20:** exactly one of `ids`/`urls`; `id` = canonical URL (Exa-compatible), `ids` accepted as deprecated alias. Per-item statuses in a 200; all fail → 200 with statuses (CHOICE). Status shape to be calqued on Exa (NV).

---

## 3. MCP `web_search_exa`

| Field | Type | Req | Default | Null | Bounds | Error | Source | Gate |
|---|---|---|---|---|---|---|---|---|
| `query` | string | yes | — | no | minLength 1 | tool error | DOC/CHOICE | Gate 0 |
| `objective` | string | yes | — | no | 1–4096 | tool error | CHOICE D26 | Gate 0 |
| `numResults` | integer | no | 10 | no | 1–100 (CHOICE) | tool error | CHOICE D26 | Gate 0 |

**Output:** one `content[].text` block: `Title / URL / Published / Author / Highlights`, separated by `---`; `_meta.searchTime` optional (not required).

---

## 4. MCP `web_fetch_exa`

| Field | Type | Req | Default | Null | Bounds | Error | Source | Gate |
|---|---|---|---|---|---|---|---|---|
| `urls` | array | yes | — | no | 1–100 (CHOICE) | tool error | CHOICE | Gate 0 |
| `maxCharacters` | integer | no | 3000 | no | min 1 | tool error | CHOICE | Gate 0 |

**v1:** shape-compatible, snapshot-only (no live fetch).

---

## 5. Error matrix

| Case | HTTP `/search` | HTTP `/contents` | MCP HTTP | MCP stdio |
|---|---|---|---|---|
| Invalid JSON | 400 `invalid_request` | 400 `invalid_request` | JSON-RPC parse error | JSON-RPC parse error |
| Unknown field | 400 `invalid_request` (CHOICE) | 400 `invalid_request` | tool error (`isError`) | tool error (`isError`) |
| Content-Type wrong/absent | **415 `unsupported_media_type`** | **415** | n/a | n/a |
| Body too large | 413 | 413 | n/a | n/a |
| `numResults` out of bounds | 400 | n/a | tool error | tool error |
| Missing auth (keyed) | 401 `unauthorized` | 401 `unauthorized` | transport 401 + `WWW-Authenticate` | **no transport**: env at launch → refuse start (D22) |
| Invalid key | 401 `unauthorized` (uniform) | 401 `unauthorized` | transport 401 | refuse start |
| Expired key | 401 `key_expired` | 401 `key_expired` | transport 401 | refuse start |
| Missing scope | 403 `forbidden` | 403 `forbidden` | transport 403 | tool error |
| Suspended/banned | 403 `account_suspended`/`account_banned` | idem | transport 403 | tool error |
| Quota | 429 `rate_limited` + `Retry-After` | idem | tool error | tool error |
| Backend unavailable | 503 `service_unavailable` | 503 | tool error | tool error |
| Timeout | 504 | 504 | tool error | tool error |
| Both `ids`+`urls` | n/a | 400 `invalid_request` | n/a | n/a |
| Unknown id/url | n/a | per-item status in 200 | n/a | n/a |
| Unknown tool | n/a | n/a | JSON-RPC error | JSON-RPC error |

**MCP spec pinned:** 2025-11-25. Input validation errors → `isError` (not `-32602`); unknown tool/malformed request/server error → JSON-RPC.

---

## 6. Decisions

- **D20** `/contents` XOR `ids`/`urls`; `id` = canonical URL; `ids` deprecated alias; per-item statuses; all fail → 200.
- **D21** `Content-Type` wrong/absent → 415 `unsupported_media_type`.
- **D22** MCP stdio: env credentials; absent/invalid → refuse start; expiry/suspension mid-run → `isError`.
- **D23** MCP HTTP: 401 transport + `WWW-Authenticate`; scope → 403 transport; invalid args → `isError`; unknown tool → JSON-RPC; spec 2025-11-25.
- **D24** Auth v1: `x-api-key` + `Authorization: Bearer` HTTP; keyless by config; MCP HTTP bearer; stdio env; OAuth LATER.
- **D25** Versioning: no `/v1` prefix; contract version + response header.
- **D26** MCP `numResults` integer 1–100; `objective` required (CHOICE).
- **D27** Unsupported → 400 `unsupported_field`; default-valued fields accepted; `type: deep` → 400 `unsupported_value`.

## 7. Open (non-blocking for Gate 0)

- [ ] `/contents` per-item status shape (calque Exa).
- [ ] MCP bounds: `web_fetch_exa.urls` min/max, string length.
- [ ] `maxCharacters` 1M vs 5M: DOC line / CHOICE.
- [ ] Filter × `type` table before Gate 1.
- [ ] `objective` consumption (S6).
- [ ] OAuth, dates, `lite` filters (later).

**Freeze:** `S2 v1.0-gate0-rc` — Gate-0 fields are DOC/CHOICE, no NV, no OBS. Later fields are explicitly 400.

## 8. Final freeze (`v1.0-gate0`)

- [x] `maxCharacters`: **DOC** — `/search.contents.text.maxCharacters` ≤1,000,000 (`exa-spec.yaml` line 3624); `/contents.text.maxCharacters` ≤5,000,000 (line 4018).
- [x] `/contents` per-item status shape: **CHOICE** — `{"id": ..., "status": "ok|not_found|not_in_index", ...}` (Exa's exact shape NV).
- [x] MCP `web_fetch_exa.urls` bounds: **CHOICE** — 1–100 items, string 1–2048.
- [x] D21 = `Content-Type` 415; MCP same-service = D18/§3.3.1.
- [x] File hash: `c2920819fd57f173f31c4b03efd45a6f8005f31eaf4e1afe4be499a112595c43` — sha256 of the frozen matrix content **before** this hash line was appended.

## 9. Minor version `v1.1` (backward-compatible, D67/D69)

Does **not** re-freeze Gate 0 (`v1.0-gate0` hash unchanged). Adds only:

- [ ] `score` (search hits): **normalized via sigmoid in [0, 1]** (D67). Replaces the raw reranker logit; ordering unchanged.
- [ ] `degraded`: **optional array of reasons** (`bm25_only`, `rerank_skipped`, …); absent or empty when nominal (D69). Never cached; counted in metrics.
- [ ] Any 503 / fallback during a gate run **invalidates the run** (D69); flag forced off during gates.