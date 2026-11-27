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


def load_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> Reranker:
    from sentence_transformers import CrossEncoder

    return Reranker(CrossEncoder(model_name))


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
        start = time.monotonic()
        budget = min(deadline, start + self._timeout)
        # Deadline/timeout already exceeded -> keep fusion order, degraded (D67).
        if start >= budget:
            return fusion, True
        pairs = [(query, t) for _, t in hits_with_text]
        raw = self._model.predict(pairs)  # type: ignore[attr-defined]
        if time.monotonic() > budget:  # scoring ran past the budget
            return fusion, True
        scored: list[tuple[float, Hit]] = []
        for (h, _), s in zip(hits_with_text, raw):
            s = float(s)
            if not math.isfinite(s):  # NaN/inf -> degraded, keep fusion (D67)
                return fusion, True
            scored.append((_sigmoid(s), h))
        scored.sort(key=lambda x: (-x[0], x[1].doc_id))
        return [h for _, h in scored], False