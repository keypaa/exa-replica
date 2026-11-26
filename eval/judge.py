"""Judge calibration (§1.5/D14).

The judge is blind: it labels `(query, doc)` only, never the system that produced
the doc. Calibration reports Cohen's κ against human labels; κ ≥ 0.6 is the
provisional threshold. The labeler (LLM) is injected; M2 does not call a model.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence

KAPPA_THRESHOLD = 0.6


def cohen_kappa(a: Sequence[int], b: Sequence[int]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    labels = set(a) | set(b)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[l] / n) * (cb[l] / n) for l in labels)
    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


class Judge:
    def __init__(self, labeler: Callable[[str, str], int]) -> None:
        self._labeler = labeler

    def judge(self, query: str, doc: str) -> int:
        return self._labeler(query, doc)


def calibrate(judge: Judge, samples: Sequence[tuple[str, str, int]]) -> float:
    preds = [judge.judge(q, d) for q, d, _ in samples]
    humans = [h for _, _, h in samples]
    return cohen_kappa(preds, humans)