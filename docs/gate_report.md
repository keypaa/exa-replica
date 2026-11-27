# Gate report — v0.1.0 (D17/D97: validated / failed / not demonstrated / not executed)

| Gate | State | Evidence |
|---|---|---|
| **Gate 0** — core API (D12) | **passed** | M1 `tests/gate/test_gate0.py` |
| **Gate 1** — MCP drop-in (replica) | **passed** | M1 `tests/gate/test_gate1.py` |
| **Gate 2** — keyed mode (D3–D11) | **passed** | M3 `tests/gate/test_gate2.py` |
| **Gate 3** — quality (D14/D19) | **not demonstrated** | The random Common Crawl T0 sample has ~no relevant docs for the dev queries; human κ is degenerate (all-0 labels). A targeted corpus is required for a real Gate 3. |
| **Gate 4** — performance (D15/D16) | **not executed** | Owner-run on the RTX Pro 6000 (cold cache, final topology) — `bench/rtx/gate4_runbook.md`. |
| **Gate 5** — scale/ops (D17) | **partial** | Determinism/idempotence/provenance verified (`test_gate5.py`); observability (D17 5d) deferred. |

## Notes
- **Gate 3 not demonstrated** is a legitimate D19 state (not a failure, not a pass). The corpus (D28/D35, random CC-MAIN-2026-43) does not contain relevant documents for the dev queries, so quality cannot be shown on it. A targeted-corpus build is the post-v0.1.0 evidence task.
- **Gate 4 not executed** — owner runs the RTX blocking run; until then v0.1.0 is a release candidate, not a perf-certified release.
- Exa-parity snapshot is ToS-blocked (D19); no parity claim is made.