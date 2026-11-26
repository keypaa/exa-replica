# Exa MCP contract fixtures

Captured **2026-11-23** from the keyless Exa MCP (`https://mcp.exa.ai/mcp`, server `exa-search-server` **3.5.1**).

| File | What it is |
|------|------------|
| `tools.json` | `tools/list` result: the two keyless tools and their input schemas |
| `search.json` | one `web_search_exa` result (3 results) |
| `fetch.json` | one `web_fetch_exa` result (1 URL, `maxCharacters` 1200) |
| `seed.jsonl` | 4 curated queries (tech, finance, code, research), each with query + objective + text result |

## Provenance

`seed.jsonl` is **curated**, not real agent traces. It is a parser/contract smoke test, **not** a golden set. Do not use it to claim quality or coverage.

## Observed behavior

- `web_search_exa` requires `query` + `objective`; `numResults` optional (default 10). Output is one text block: `Title / URL / Published / Author / Highlights`, results separated by `---`.
- `web_fetch_exa` requires `urls[]`; `maxCharacters` optional (default 3000). Output starts with `# <Title>`, then `URL:`, `Published:`, then markdown.
- Unknown publication dates render as `Published: N/A` — do **not** substitute `warc-date` (that is the crawl date).
- `_meta.searchTime` appears on some calls and is absent on others; do not make it a required field.

## Capture path

The keyless MCP is reachable with `initialize` → `tools/list` → `tools/call` (JSON-RPC over HTTP, SSE responses). The session id is returned in the `Mcp-Session-Id` response header and must be sent on subsequent calls.
