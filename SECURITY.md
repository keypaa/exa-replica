# Security Policy (P1, D91)

## Reporting a vulnerability

Report suspected vulnerabilities privately via GitHub Security Advisories
("Report a vulnerability" on the repo). Do not open a public issue.

## Hardening commitments (v1)

- API keys: hex secret, HMAC pepper, `hash_version`, fixed length, uniform
  failure; prefix-only logs; rotation with grace; revocable (D3–D7).
- Auth: `x-api-key` + Bearer; keyless is explicit, limited, and distinct from
  authenticated mode; an invalid key is never treated as "no key" (D8/D24).
- Transport: TLS terminates at a proxy; MCP transport host/origin allowlist
  (DNS-rebinding protection) enabled in production (D91; M0 disables it for
  local dev only).
- Input: size limits, 413 on overflow, CORS off, path containment, no
  eval/exec/pickle, redaction, IPC 0600 (D91).
- Supply chain: lockfiles committed (`uv.lock`, `Cargo.lock`); `pip-audit` +
  `cargo audit`; gitleaks in CI (D17 5e / D102).
- SSRF (live fetch) is out of v1 (D91).

## Supported versions

v0.x — security fixes on the latest release line only.