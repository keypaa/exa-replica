"""Static orchestrator (D86): executes a TierPlan in D66 order.

v1: encode (dense adapter) → BM25 ∥ dense → RRF fusion → rerank (auto only,
D67) → contents → highlights. Deadline checked between steps; no memoization.
The reranker is optional (lite = passthrough); when it skips/times out the
fusion order is kept and `degraded=True` (D67/D69). Workers/queues are S7.
"""

from __future__ import annotations

from dataclasses import dataclass

from exa_replica.application.fusion import fuse
from exa_replica.application.highlights import highlights
from exa_replica.application.plans import TierPlan
from exa_replica.domain.models import Filters, Hit
from exa_replica.ports.content import ContentStorePort
from exa_replica.ports.index import DenseIndex, LexicalIndex
from exa_replica.ports.rerank import RerankPort

_RERANK_TOP_N = 50


@dataclass(frozen=True, slots=True)
class DocResult:
    doc_id: str
    score: float
    passage_id: str
    text: str
    highlights: tuple[str, ...]
    status: str  # ok | not_found | not_in_index (D20)
    degraded: bool = False  # rerank skipped/timed out (D67/D69)


class Orchestrator:
    def __init__(
        self,
        dense: DenseIndex,
        lexical: LexicalIndex,
        store: ContentStorePort,
        plan: TierPlan,
        reranker: RerankPort | None = None,
    ) -> None:
        self._dense = dense
        self._lexical = lexical
        self._store = store
        self._plan = plan
        self._reranker = reranker

    def _passage_text(self, dh: Hit) -> str:
        for p, t in self._store.get_passages(dh.doc_id):
            if p.passage_id == dh.passage_id:
                return t
        return self._store.get_text(dh.doc_id) or ""

    def run(
        self, query: str, filters: Filters, k: int, deadline: float
    ) -> list[DocResult]:
        if deadline <= 0:
            return []
        dense_hits = self._dense.search(query, filters, k, deadline)
        lexical_hits = self._lexical.search(query, filters, k, deadline)
        fused: list[Hit] = [
            Hit(dh.doc_id, dh.score, dh.passage_id)
            for dh in fuse(lexical_hits, dense_hits)
        ]

        degraded = False
        if "rerank" in self._plan.stages and self._reranker is not None and fused:
            pairs = [
                (Hit(dh.doc_id, dh.score, dh.passage_id), self._passage_text(dh))
                for dh in fused[:_RERANK_TOP_N]
            ]
            reranked, degraded = self._reranker.rerank(query, pairs, deadline)
            fused = reranked

        out: list[DocResult] = []
        for dh in fused:
            text = self._store.get_text(dh.doc_id)
            if text is None:  # not found or taken down (D52)
                continue
            hl = highlights(text, query) if "highlights" in self._plan.stages else ()
            out.append(
                DocResult(
                    dh.doc_id, dh.score, dh.passage_id, text, tuple(hl), "ok", degraded
                )
            )
        return out