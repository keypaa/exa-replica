"""Rerank port (D85/D95): the application depends on this, not the adapter."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from exa_replica.domain.models import Hit


class RerankPort(Protocol):
    def rerank(
        self,
        query: str,
        hits_with_text: Sequence[tuple[Hit, str]],
        deadline: float,
    ) -> tuple[list[Hit], bool]: ...