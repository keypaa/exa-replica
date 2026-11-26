# M4 Contents/Highlights S1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the S1 dense highlight selection (D84 R1) behind the S0 default, measure it with the D94 metric, and decide R1 vs S0 — S0 already shipped in M1.

**Architecture:** S1 = cosine(sentence, guiding text) via the encode pool, adopted only if gain ≥2 pts IC95 and latency ≤ R2 (D84). D94 metric (success@3 + precision) with separate κ.

**Tech Stack:** Python 3.12, the M1 encoder pool, the M2 eval harness.

**Spec:** `docs/EXA_REPLICA_RESEARCH.md` (D84, D94, D66, D71, D61), `docs/s2_contract_matrix.md`.

## Global Constraints

- S0 remains default; S1 only if R1 passes (D84).
- `lite` forces S0 (D84).
- No LLM highlights in v1.
- Non-regression: S0 byte-exact; S1 D63 tolerance + same sentence choice (D84).

## Review Focus

- **S1 not adopted without IC95:** gain must be significant (D84). Test: `test_s1_requires_ic95`.
- **lite forces S0:** even if S1 wins overall (D84). Test: `test_lite_forces_s0`.
- **κ uncalibrated:** highlights not used for R1 if κ low (D94). Test: `test_kappa_uncalibrated`.
- **Non-regression S0:** byte-exact same output (D84). Test: `test_s0_byte_exact`.
- **R2 exceeded:** switch S1→S0 + log (D84). Test: `test_r2_switch`.

---

### Task 1: S1 dense selection (D84 R1)

**Files:**
- Create: `application/highlights_s1.py`; Test: `tests/application/test_highlights_s1.py`

**Interfaces:**
- Consumes: sentence split + guiding text + encoder. Produces: `highlights_s1(...) -> list[str]`.

- [ ] **Step 1: Write failing test** `test_s1_ranks_by_cosine`, `test_lite_forces_s0`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement S1 (D84) behind a flag; lite forces S0.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: highlights S1 (D84 R1)`.

### Task 2: R1 selection rule + R2 budget (D84)

**Files:**
- Create: `eval/highlights_ab.py`; Test: `eval/tests/test_highlights_ab.py`

**Interfaces:**
- Consumes: S0, S1, D94 metric. Produces: adopt/reject S1; R2 switch.

- [ ] **Step 1: Write failing test** `test_s1_requires_ic95`, `test_r2_switch`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement R1 (paired bootstrap, gain ≥2 pts) + R2 (p95 > budget → S0 + log).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: R1/R2 highlight selection (D84)`.

### Task 3: D94 metric + κ (D94)

**Files:**
- Create: `eval/highlight_metric.py`; Test: `eval/tests/test_highlight_metric.py`

**Interfaces:**
- Produces: success@3 highlight + mean precision top-10; separate κ.

- [ ] **Step 1: Write failing test** `test_success_at_3`, `test_precision_all_top10`, `test_kappa_uncalibrated`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Implement D94 metric.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: D94 highlight metric`.

### Task 4: Non-regression (D84)

**Files:**
- Create: `tests/application/test_highlights_nonreg.py`

**Interfaces:**
- Consumes: S0 (M1) + S1 (Task 1); selection rule from Task 2. Produces: byte-exact S0 baseline; S1 same-sentence-choice check.

- [ ] **Step 1: Write failing test** `test_s0_byte_exact`, `test_s1_same_sentence_choice`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3:** Pin S0 output; S1 tolerance + same choice.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `test: highlights non-regression (D84)`.