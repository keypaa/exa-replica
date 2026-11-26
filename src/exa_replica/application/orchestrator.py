"""Static orchestrator (D86): executes a TierPlan in D66 order.

v1: encode (done by the dense adapter) → BM25 ∥ dense → RRF fusion → rerank
(passthrough) → contents → highlights. Deadline checked between steps; no
memoization. Workers/bounded queues belong to S7.
"""

from __future__ import annotations

from dataclasses import dataclass

from exa_replica.application.fusion import fuse
from exa_replica.application.highlights import highlights
from exa_replica.application.plans import TierPlan
from exa_replica.domain.models import Filters
from exa_replica.ports.content import ContentStorePort
from exa_replica.ports.index import DenseIndex, LexicalIndex


@dataclass(frozen=True, slots=True)
class DocResult:
    doc_id: str
    score: float
    passage_id: str
    text: str
    highlights: tuple[str, ...]
    status: str  # ok | not_found | not_in_index (D20)


class Orchestrator:
    def __init__(
        self,
        dense: DenseIndex,
        lexical: LexicalIndex,
        store: ContentStorePort,
        plan: TierPlan,
    ) -> None:
        self._dense = dense
        self._lexical = lexical
        self._store = store
        self._plan = plan

    def run(
        self, query: str, filters: Filters, k: int, deadline: float
    ) -> list[DocResult]:
        if deadline <= 0:
            return []
        dense_hits = self._dense.search(query, filters, k, deadline)
        lexical_hits = self._lexical.search(query, filters, k, deadline)
        out: list[DocResult] = []
        for dh in fuse(lexical_hits, dense_hits):
            text = self._store.get_text(dh.doc_id)
            if text is None:  # not found or taken down (D52)
                continue
            hl = highlights(text, query) if "highlights" in self._plan.stages else ()
            out.append(
                DocResult(dh.doc_id, dh.score, dh.passage_id, text, tuple(hl), "ok")
            )
        return out