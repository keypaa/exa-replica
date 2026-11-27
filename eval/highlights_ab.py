"""R1 selection rule + R2 budget (D84).

Adopt S1 only if the paired gain is ≥2 points with IC95 lower > 0 (paired
bootstrap). If S1 p95 exceeds the R2 budget, switch back to S0 and log.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from eval.highlight_metric import kappa_uncalibrated

_MIN_GAIN = 0.02  # 2 points (D84)
_N_BOOT = 10_000


def adopt_s1(
    s0_scores: Sequence[float],
    s1_scores: Sequence[float],
    min_gain: float = _MIN_GAIN,
    n_boot: int = _N_BOOT,
    seed: int = 0,
) -> bool:
    diffs = [b - a for a, b in zip(s0_scores, s1_scores)]
    if not diffs:
        return False
    gain = sum(diffs) / len(diffs)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        sample = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        boots.append(sum(sample) / len(sample))
    boots.sort()
    ci_low = boots[int(0.025 * n_boot)]
    return gain >= min_gain and ci_low > 0.0


def r2_switch(s1_p95_ms: float, budget_ms: float) -> bool:
    """True -> S1 p95 over budget, fall back to S0 (D84 R2)."""
    return s1_p95_ms > budget_ms


def decide_s1(
    s0_scores: Sequence[float],
    s1_scores: Sequence[float],
    p95_ms: float,
    kappa: float,
    budget_ms: float,
    min_gain: float = _MIN_GAIN,
) -> tuple[bool, dict]:
    """Compose R1 (IC95) + κ gate + R2 budget -> (adopt, log_event) (D84/D94)."""
    if kappa_uncalibrated(kappa):
        return False, {"decision": "reject", "reason": "kappa_uncalibrated", "kappa": kappa}
    if r2_switch(p95_ms, budget_ms):
        return False, {"decision": "s0", "reason": "r2_exceeded", "p95_ms": p95_ms}
    adopt = adopt_s1(s0_scores, s1_scores, min_gain=min_gain)
    return adopt, {
        "decision": "s1" if adopt else "s0",
        "reason": "ic95" if adopt else "no_ic95",
    }