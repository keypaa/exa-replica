"""Index ports (D85). One Protocol per retrieval branch; no add/delete in v1.

Each search is bound to the `index_version` fixed for the request (§1.3.1).
An unsupported filter raises `UnsupportedFilter`.
"""

from __future__ import annotations

from typing import Protocol

from exa_replica.domain.models import Filters, Hit


class DenseIndex(Protocol):
    def search(
        self, query: str, filters: Filters, k: int, deadline: float
    ) -> list[Hit]: ...

    def stats(self) -> dict[str, float | int | str]: ...

    def version(self) -> str: ...


class LexicalIndex(Protocol):
    def search(
        self, query: str, filters: Filters, k: int, deadline: float
    ) -> list[Hit]: ...

    def stats(self) -> dict[str, float | int | str]: ...

    def version(self) -> str: ...