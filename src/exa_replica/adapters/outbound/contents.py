"""Contents provider (D20/D84): `/contents` reads stored text + S0 highlights.

Per-item status is `ok` / `not_found` (D20). A taken-down or absent document is
`not_found` (the store returns None). `not_in_index` (duplicate) arrives with
dedup in a later task.
"""

from __future__ import annotations

from collections.abc import Sequence

from exa_replica.application.highlights import highlights
from exa_replica.ports.content import ContentStorePort


class ContentsProvider:
    def __init__(self, store: ContentStorePort) -> None:
        self._store = store

    def fetch(self, urls: Sequence[str]) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for url in urls:
            text = self._store.get_text(url)
            if text is None:
                out.append(
                    {"url": url, "status": "not_found", "text": None, "highlights": []}
                )
            else:
                out.append(
                    {
                        "url": url,
                        "status": "ok",
                        "text": text,
                        "highlights": highlights(text),
                    }
                )
        return out