# M5 Hardening + Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move to the final D89 topology (gateway + separate workers) + D90 cache, run the single test-split Gate 3, the blocking Gate 4 (cold cache), Gate 5 (D17), harden per D91, pick the public name, and cut v0.1.0.

**Architecture:** Gateway (HTTP+MCP) + GPU worker (encode/R0/rerank) + CPU worker(s) (BM25/contents/highlights) over Unix socket+msgpack (D89); LRU caches (D90); systemd units; atomic generation switch (D68).

**Tech Stack:** Python 3.12, FastAPI, `mcp` 2.x, msgpack, systemd, k6 (Gate 4), OTel.

**Spec:** `docs/EXA_REPLICA_RESEARCH.md` (D17, D45, D68, D89, D90, D91, D97, D98, D16), `docs/s2_contract_matrix.md`.

## Global Constraints

- Final topology D89; cache D90 (cold-cache gate).
- Gate 3 on test split **once** (D97); Gate 4 blocking on final topology, cold cache.
- D91 hardening (TLS proxy, size limits, CORS off, IPC 0600, no eval/exec/pickle).
- Public name neutral, no "exa" (D97); v0.1.0 SemVer (D98).

## Review Focus

- **Two builds in VRAM during switch:** budget 2×V_gpu or short dense outage (D68). Test: `test_switch_peak_or_outage`.
- **Cache not warmed at Gate 4:** cold cache validated (D90). Test: `test_gate4_cold_cache`.
- **Degraded never cached:** `degraded` responses not stored (D90). Test: `test_degraded_not_cached`.
- **Takedown after cache:** excluded doc absent post-cache (D52). Test: `test_takedown_after_cache`.
- **Public name:** no "exa", non-affiliation (D97). Test: `test_public_name`.

---

### Task 1: Final topology D89 (gateway + workers)

**Files:**
- Modify: `deploy/gateway.service`, `deploy/worker-gpu.service`, `deploy/worker-cpu.service`, `src/exa_replica/entrypoints/*` (stubs from M0); Test: `tests/test_topology.py`

**Interfaces:**
- Produces: gateway + GPU worker + CPU worker over Unix socket+msgpack.

- [ ] **Step 1: Write failing test** `test_gateway_workers`, `test_ipc_socket_0600`, `test_build_id_not_mixed`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement D89 topology + systemd units.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: final topology D89`.

### Task 2: Cache D90 (LRU RAM)

**Files:**
- Create: `application/cache.py`; Test: `tests/application/test_cache.py`

**Interfaces:**
- Produces: embedding + contents LRU; full-response off.

- [ ] **Step 1: Write failing test** `test_embedding_cache_key`, `test_contents_cache_key`, `test_degraded_not_cached`, `test_takedown_after_cache`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement D90.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: LRU caches (D90)`.

### Task 3: Generation switch D68

**Files:**
- Create: `deploy/switch.sh`, `src/exa_replica/bootstrap/switch.py`; Test: `tests/test_switch.py`

**Interfaces:**
- Produces: atomic generation switch; 2×V_gpu peak or short dense outage.

- [ ] **Step 1: Write failing test** `test_switch_peak_or_outage`, `test_atomic`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement D68 switch.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: generation switch (D68)`.

### Task 4: D91 hardening

**Files:**
- Modify: `adapters/inbound/http.py`, `deploy/*`; Test: `tests/test_security.py`

**Interfaces:**
- Produces: TLS proxy, size limits, CORS off, IPC 0600, no eval/exec/pickle.

- [ ] **Step 1: Write failing test** `test_413`, `test_cors_preflight_refused`, `test_path_traversal`, `test_no_pickle`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Apply D91.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: D91 hardening`.

### Task 5: Gate 3 (test) + Gate 4 (blocking) + Gate 5

**Files:**
- Create: `tests/gate/test_gate3_test.py`, `tests/gate/test_gate4.py`, `tests/gate/test_gate5.py`

- [ ] **Step 1: Write failing test** `test_gate3_test_single`, `test_gate4_cold_cache`, `test_gate5_ops`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Run Gate 3 (test, once), Gate 4 (blocking, cold cache), Gate 5 (D17).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `test: Gate 3/4/5 (D97)`.

### Task 6: Public name + v0.1.0 release (D97/D98)

**Files:**
- Create: `CHANGELOG.md`, `README.md`; Modify: `pyproject.toml` (version 0.1.0)

**Interfaces:**
- Produces: public name (neutral), v0.1.0, CHANGELOG.

- [ ] **Step 1: Write failing test** `test_public_name`, `test_version_0_1_0`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Set public name, bump to 0.1.0, write CHANGELOG/README.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `chore: public name + v0.1.0 (D97/D98)`.