# Sift

Open-source, self-hosted, Exa-type search replica: **MCP + HTTP** (`/search`,
`/contents`) over a full pipeline (acquisition → parse → embed → index → serve).

> **Naming:** **Sift** is the public name (D97). The internal code name is
> `exa-replica` (D95). PyPI `sift` is already taken, so the distribution name will
> be a variant (e.g. `sift-search`) at publish time. This project is **not
> affiliated with Exa**.

## Status

v0.1.0 release candidate (M0–M5 complete). Gate 0/1/2 ✓; **Gate 3 not
demonstrated** (the random T0 corpus lacks relevant docs — see
`docs/gate_report.md`); Gate 4 owner-run on the RTX Pro 6000; Gate 5 partial.

## Quickstart

```bash
uv python pin 3.12 && uv sync
make check            # ruff + mypy --strict + import-linter + pytest + audit
uv run python -m exa_replica.entrypoints.search   # single-process fallback
```

## Architecture (D95)

`src/exa_replica/` = `domain/` (pure) · `ports/` · `application/` (SearchService,
TierPlan, orchestrator) · `adapters/inbound/` (http FastAPI, mcp) · `adapters/
outbound/` (store, encoder, ann, bm25, contents) · `bootstrap/` (composition root,
ipc, switch) · `entrypoints/` (per pool). `eval/ bench/` are outside the package.

## Documentation

- `AGENTS.md` — governance source of truth.
- `docs/EXA_REPLICA_RESEARCH.md` — decisions D0–D103.
- `docs/s2_contract_matrix.md`, `docs/s4_*` — contracts.
- `docs/hardware_reference.md`, `docs/evidence_*` — measurement profiles + evidence.
- `bench/rtx/` — owner-run RTX runbook (Gate 4).