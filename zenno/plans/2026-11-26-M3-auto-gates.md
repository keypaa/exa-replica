# M3 Auto + Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add keyed mode (auth/keys/quotas/accounts/Postgres), the real cross-encoder reranker (D67), and pass Gate 2 (keyed), Gate 3 (quality on dev), Gate 4 (pilot, non-blocking).

**Architecture:** Keyed v1 (D3–D11) in Postgres; auto tier with real reranker behind the D85/D86 interfaces; gates 2/3/4 per D97.

**Tech Stack:** Postgres, FastAPI, sentence-transformers (reranker), the M1/M2 stack.

**Spec:** `docs/EXA_REPLICA_RESEARCH.md` (D3–D11, D13/D14, D15/D16, D66, D67, D97), `docs/s2_contract_matrix.md`, `docs/s4_manifest_schemas_v0.md`.

## Global Constraints

- Keyed mode per D3–D11; 429 vs 503; `X-Request-Id`.
- Reranker cross-encoder EN+FR, p95 ≤800 ms (D66/D67); passthrough removed.
- Gate 4 pilot non-blocking (D97); no test-split run (that is M5).
- `degraded` for rerank skip (D67/D69).

## Review Focus

- **Key never in logs:** only prefix logged (D91). Test: `test_key_not_in_logs`.
- **Reranker timeout:** >800 ms → fusion order + `degraded` (D67). Test: `test_rerank_timeout`.
- **Quota vs overload:** 429 (quota) ≠ 503 (queue full) (D9/D11). Test: `test_429_vs_503`.
- **Gate 4 pilot not gating:** pilot results recorded, not blocking (D97). Test: `test_gate4_pilot_nonblocking`.
- **Quota without cache:** a keyed response counts quota (D9); the cache-hit variant is tested in M5 (D90). Test: `test_quota_counted`.

---

### Task 1: Postgres schema + identity (D2–D7)

**Files:**
- Create: `adapters/outbound/pg/schema.sql`, `adapters/outbound/pg/keys.py`; Test: `tests/adapters/test_pg_keys.py`

**Interfaces:**
- Produces: `accounts`, `api_keys` tables; `ApiKeyService` (generate/verify/rotate/revoke).

- [ ] **Step 1: Write failing test** `test_key_format`, `test_hash_hmac`, `test_expiry`, `test_rotation_grace`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement schema + `ApiKeyService` (D3–D7).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: Postgres identity + keys (D2–D7)`.

### Task 2: Rate limits + accounts/bans (D9/D10)

**Files:**
- Create: `adapters/outbound/pg/limits.py`; Test: `tests/adapters/test_limits.py`

**Interfaces:**
- Produces: token bucket + daily counter; suspend/ban checks.

- [ ] **Step 1: Write failing test** `test_token_bucket`, `test_daily_counter`, `test_ban_blocks`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement D9/D10.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: rate limits + bans (D9/D10)`.

### Task 3: Error envelope + auth order (D11)

**Files:**
- Modify: `adapters/inbound/http.py`; Test: `tests/adapters/test_errors.py`

**Interfaces:**
- Produces: `{requestId,error,tag}` + `X-Request-Id`; 429/503/413/415/409.

- [ ] **Step 1: Write failing test** `test_429_vs_503`, `test_413`, `test_415`, `test_409`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement D11 envelope + auth order.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: error envelope + auth order (D11)`.

### Task 4: Real reranker (D67)

**Files:**
- Create: `adapters/outbound/reranker.py`; Test: `tests/adapters/test_reranker.py`

**Interfaces:**
- Consumes: query + top-50. Produces: reranked hits + sigmoid score.

- [ ] **Step 1: Write failing test** `test_rerank_changes_order`, `test_rerank_timeout_fusion`, `test_score_sigmoid`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement cross-encoder (D67), `max_pair_tokens` per D67.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: cross-encoder reranker (D67)`.

### Task 5: Gate 2 tests (keyed)

**Files:**
- Create: `tests/gate/test_gate2.py`; Test: same.

- [ ] **Step 1: Write failing test** `test_gate2_keyed_mode`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Wire keyed fixtures.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `test: Gate 2 keyed (D97)`.

### Task 6: Gate 3 on dev + Gate 4 pilot

**Files:**
- Create: `tests/gate/test_gate3_dev.py`, `tests/gate/test_gate4_pilot.py`

- [ ] **Step 1: Write failing test** `test_gate3_dev_quality`, `test_gate4_pilot_nonblocking`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Run gate 3 on dev (D14/D19); gate 4 pilot (D15/D16).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `test: Gate 3 dev + Gate 4 pilot (D97)`.