"""Cross-encoder reranker (D67).

Reranks the top-N fused hits with a cross-encoder; the raw score is passed
through a sigmoid into (0,1). If the deadline (p95 ≤800 ms, D66) is exceeded the
fusion order is kept and `degraded=True` (D67/D69). The model is injected; M3
tests use a fake (no GPU).
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence

from exa_replica.domain.models import Hit


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class Reranker:
    def __init__(self, model: object, timeout_s: float = 0.8) -> None:
        self._model = model
        self._timeout = timeout_s

    def rerank(
        self,
        query: str,
        hits_with_text: Sequence[tuple[Hit, str]],
        deadline: float,
    ) -> tuple[list[Hit], bool]:
        fusion = [h for h, _ in hits_with_text]
        if not fusion:
            return [], False
        # Deadline already exceeded -> keep fusion order, mark degraded (D67).
        if deadline <= time.monotonic():
            return fusion, True
        pairs = [(query, t) for _, t in hits_with_text]
        raw = self._model.predict(pairs)  # type: ignore[attr-defined]
        scored = [(_sigmoid(float(s)), h) for (h, _), s in zip(hits_with_text, raw)]
        if deadline <= time.monotonic():  # scoring ran past the deadline
            return fusion, True
        scored.sort(key=lambda x: (-x[0], x[1].doc_id))
        return [h for _, h in scored], False