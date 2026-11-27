"""Contents provider (D20/D84): `/contents` reads stored text + S0 highlights.

Per-item status `ok` / `not_found` (D20). A taken-down or absent document is
`not_found`. The contents cache (D90) is checked first; exclusions (D52) are
applied after the cache read so a takedown is immediate.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from exa_replica.application.cache import CacheLayer
from exa_replica.application.highlights_s1 import select_highlights
from exa_replica.ports.content import ContentStorePort


class ContentsProvider:
    def __init__(
        self,
        store: ContentStorePort,
        cache: CacheLayer | None = None,
        build_id: str = "",
        is_excluded: Callable[[str], bool] | None = None,
    ) -> None:
        self._store = store
        self._cache = cache
        self._build_id = build_id
        self._is_excluded = is_excluded or (lambda _url: False)

    def fetch(self, urls: Sequence[str]) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for url in urls:
            if self._is_excluded(url):  # D52: takedown applied after cache read
                out.append({"url": url, "status": "not_found", "text": None, "highlights": []})
                continue
            text = self._cache.get_contents(self._build_id, url) if self._cache else None
            if text is None:
                text = self._store.get_text(url)
                if text is not None and self._cache is not None:
                    self._cache.put_contents(self._build_id, url, text)
            if text is None:
                out.append({"url": url, "status": "not_found", "text": None, "highlights": []})
            else:
                out.append(
                    {
                        "url": url,
                        "status": "ok",
                        "text": text,
                        "highlights": select_highlights(text, "", "auto", s1_enabled=False),
                    }
                )
        return out