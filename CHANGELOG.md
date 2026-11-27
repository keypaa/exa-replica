# Changelog

All notable changes to this project are documented here. Versioning is SemVer
(D98); the API/MCP surface is additive within 0.x.

## 0.1.0 — 2026-11-27

First release candidate (M0–M5). Open-source, self-hosted, Exa-type search
replica (MCP + HTTP).

- **Skeleton (M0):** D95 layered layout (domain/ports/application/adapters/
  bootstrap/entrypoints), import-linter (D96), CI + DCO, versioned contract
  snapshots (OpenAPI + `tools/list`, D103), MCP target 2026-07-28 / mcp 2.x (D89).
- **Contract e2e (M1):** `/search` (lite/auto) + `/contents` (S0 highlights) +
  both MCP tools; passage chunker (D60), content store (D48–D50), BM25 (D83),
  dense R0 (D82), RRF fusion, highlights S0 (D84). Gate 0 + Gate 1.
- **Eval (M2):** harness (recall/nDCG/MRR), golden-set builder (D93), judge (κ),
  paired pilot σ, D93 growth, D81 provisional model choice.
- **Auto + gates (M3):** keyed mode (Postgres identity D2–D7, limits/bans D9–D10,
  error envelope/auth order D11), real cross-encoder reranker (D67). Gate 2 (keyed),
  Gate 3 dev, Gate 4 pilot (non-blocking).
- **Highlights S1 (M4):** S1 dense selection behind S0 default (D84 R1), R1/R2
  rule, D94 metric.
- **Hardening + release (M5):** D89 topology (gateway + workers, Unix socket +
  msgpack), D90 LRU caches, D68 generation switch, D91 hardening, Gate 5 (D17).
  Gate 3 (test split) + Gate 4 (blocking) are owner-run on the reference box.

### Compatibility
API compatible with the Exa `/search` + `/contents` surface and the keyless MCP
`web_search_exa` / `web_fetch_exa` tools. This project is **not affiliated with
Exa**; the **public name is still pending** (D97) and will be chosen before first
publication.