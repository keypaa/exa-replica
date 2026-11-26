"""SearchService — the single frozen application entrypoint (D86, §1.3.1/D89).

`SearchService.run` is the canonical entrypoint; the internal composition
(Orchestrator, TierPlan) is an implementation detail and is not a separate
public name.
"""

from __future__ import annotations

from exa_replica.application.orchestrator import Orchestrator
from exa_replica.domain.models import Filters, Hit


class SearchService:
    def __init__(self, orchestrator: Orchestrator) -> None:
        self._orchestrator = orchestrator

    def run(
        self,
        query: str,
        deadline: float,
        filters: Filters | None = None,
        k: int = 10,
    ) -> list[Hit]:
        return self._orchestrator.run(
            query, filters or Filters(), k, deadline
        )