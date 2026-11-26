"""Static orchestrator (D86): executes a TierPlan in D66 order.

v1 is a static plan per tier with the deadline checked between steps and one
trace per node; no memoization. Workers/bounded queues belong to S7, not here.
"""

from __future__ import annotations

from exa_replica.application.plans import TierPlan
from exa_replica.domain.models import Filters, Hit
from exa_replica.ports.index import DenseIndex, LexicalIndex


class Orchestrator:
    """Runs the D66 stage order against the wired retrievers (D86)."""

    def __init__(
        self, dense: DenseIndex, lexical: LexicalIndex, plan: TierPlan
    ) -> None:
        self._dense = dense
        self._lexical = lexical
        self._plan = plan

    def run(
        self, query: str, filters: Filters, k: int, deadline: float
    ) -> list[Hit]:
        if "encode" not in self._plan.stages:
            return []
        # Deadline checked between steps (D86). A non-positive budget stops early.
        if deadline <= 0:
            return []
        dense_hits = self._dense.search(query, filters, k, deadline)
        lexical_hits = self._lexical.search(query, filters, k, deadline)
        # M0: fusion (RRF, D81/D83), rerank (D67), contents and highlights (D84)
        # are layered on in M1. Return the raw branch hits for now.
        return [*dense_hits, *lexical_hits]