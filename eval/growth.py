"""D93 growth decision.

`n_test = max(100, ceil((1.96·σ/h)²))` rounded up to 50, capped at 400. Decided
on dev only, before any test run (D14). σ is the paired-diff SD from the pilot.
"""

from __future__ import annotations

import math


def n_test(sigma: float, h: float, cap: int = 400, floor: int = 100) -> int:
    if sigma <= 0 or h <= 0:
        n = floor
    else:
        n = math.ceil((1.96 * sigma / h) ** 2)
    n = max(floor, n)
    n = math.ceil(n / 50) * 50  # round up to 50
    return min(n, cap)