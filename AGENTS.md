# AGENTS.md — Exa Replica agent contract (P0, D101)

This file is the **source of truth** for agent governance. `CLAUDE.md` is a
pointer to this file only. Every task, issue, and PR maps to a pillar below and
cites the decision (`Dxx`) it implements.

Entrypoint canonique = `SearchService.run` (§1.3.1/D89) ; `SearchPipeline` = détail interne, ne pas nommer dans les plans

## Pillars (apply to every gate)

- **P0 Agent governance** — `CLAUDE.md` ↔ `AGENTS.md`, versioned; every task maps
  to a pillar; the plan/spec references the pillars; no work outside them without
  an ADR; anti-drift checks (§1.6).
- **P1 Security** — secure development; API key generation/storage/rotation/
  revocation; auth; rate limits; bans; user management; input validation; path
  containment; redaction; dependency/supply chain; secrets (D91).
- **P2 Observability** — structured logs, metrics, traces per stage, per-tier
  QPS/latency, resource usage (D17 5d).
- **P3 Resource observability** — GPU-seconds per request, VRAM/RAM/CPU
  utilization, throughput; capacity planning, not billing (D15 4c / D17 5d).

## Development rules (D102)

- Python 3.12; `mypy --strict` on `src/exa_replica/`; `ruff`; `import-linter`
  blocking, down-only (D96).
- Coverage ≥80% lines on `domain/` + `application/`; `adapters/` excluded
  (covered by contract tests).
- Conventional commits; PR ≤400 lines; DCO `Signed-off-by` (D98).
- Every code choice cites the `Dxx` decision it implements (traceability).
- `make check` (ruff + mypy + import-linter + pytest + gitleaks + pip-audit) is
  green before merge.

## Layout (D95)

`src/exa_replica/` = `domain/` (pure) · `ports/` (D85) · `application/`
(SearchService, TierPlan, orchestrator D86) · `adapters/inbound/` (http FastAPI,
mcp) · `adapters/outbound/` (store, encoder, ann, contents) · `bootstrap/`
(composition root D92) · `entrypoints/` (one per pool D89). Optional Rust crate
`ann-core` (R1 only, D82). `eval/ bench/` live outside the product package.

## Anti-drift checklist (PR)

- Scope matches the pillar; no unrelated changes.
- Tests/benchmarks updated; ADR for any exception.
- File/complexity limits respected; OpenAPI + `tools/list` updated or justified.
- DoD met: code + tests + docs + observability + security, as applicable.

## Definition of done per task

Code + tests (RED→GREEN) + docs + observability + security checklist, as
applicable, with the `Dxx` reference and a green `make check`.