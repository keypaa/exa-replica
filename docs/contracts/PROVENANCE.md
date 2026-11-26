# Contract artifacts — provenance (D71 / D103)

## exa-openapi-2.0.0.yaml
- **Source (official):** https://exa.ai/docs/exa-spec.yaml
- **Consulted:** 2026-11-26
- **Version:** OpenAPI 3.1.0, `info.version` = 2.0.0
- **sha256:** `d625c66c6bbcdf0b5fe57ccc74bd02005ae888f0f862e16e127722ddb1af499b`
- **Endpoints observed:** `/search`, `/contents`, `/answer`, `/findSimilar` (deprecated), `/monitors*`, `/agent/runs*`
- **Use:** versioned contract artifact (D103); compared in CI. Subject to Exa ToS (D71); no API calls made.

## MCP SDK license (M0 precondition, D89)
- **Repo:** modelcontextprotocol/python-sdk, `main`
- **License:** MIT (Copyright 2024 Anthropic, PBC) → passes D57.
- **Consulted:** 2026-11-26

## MCP spec version (M0 precondition, D23/D89 amended)
- **Target:** revision marked **"Current"** on the official Versioning page at M0 freeze → **2026-07-28** (replaces 2025-11-25, now "Final").
- **SDK:** `mcp` (Python) 2.x (PyPI 2.3.0; v2.0.0 stable) serves all prior revisions from the same server.
- **Constraint:** no tool depends on a server-initiated request (elicitation/sampling/roots removed in 2026-07-28).
- **Consulted:** 2026-11-26