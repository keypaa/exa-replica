"""D94 highlight metric: success@3 + mean precision@10, with a separate κ gate.

`kappa_uncalibrated` gates R1: highlights are not used for R1 if the judge κ is
below the threshold (D94).
"""

from __future__ import annotations

from collections.abc import Sequence

KAPPA_THRESHOLD = 0.6


def success_at_3(highlights: Sequence[str], relevant: set[str]) -> float:
    return 1.0 if any(h in relevant for h in highlights[:3]) else 0.0


def mean_precision_top10(ranked: Sequence[str], relevant: set[str]) -> float:
    top = ranked[:10]
    if not top:
        return 0.0
    return sum(1 for r in top if r in relevant) / len(top)


def kappa_uncalibrated(kappa: float, threshold: float = KAPPA_THRESHOLD) -> bool:
    return kappa < threshold