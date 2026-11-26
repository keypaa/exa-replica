"""Content ports (D85/D95): the store and contents seams the application uses."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from exa_replica.domain.models import Passage


class ContentStorePort(Protocol):
    def get_text(self, url_canonical: str) -> str | None: ...

    def get_passages(
        self, url_canonical: str
    ) -> list[tuple[Passage, str]]: ...


class ContentsPort(Protocol):
    def fetch(self, urls: Sequence[str]) -> list[dict[str, object]]: ...