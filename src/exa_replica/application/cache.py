"""LRU caches (D90): embedding + contents; full-response OFF; degraded never cached.

Keys: embedding = (model, prompt_hash, query); contents = (build_id, url).
Exclusions (takedown) are applied after the cache read (D52). Bounded LRU in RAM.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TypeVar

T = TypeVar("T")


class LRU:
    def __init__(self, maxsize: int = 1024) -> None:
        self._d: OrderedDict[object, object] = OrderedDict()
        self._max = maxsize

    def get(self, key: object) -> object | None:
        if key in self._d:
            self._d.move_to_end(key)
            return self._d[key]
        return None

    def put(self, key: object, val: object) -> None:
        self._d[key] = val
        self._d.move_to_end(key)
        while len(self._d) > self._max:
            self._d.popitem(last=False)


def embedding_key(model: str, prompt_hash: str, query: str) -> tuple[str, str, str]:
    return (model, prompt_hash, query)


def contents_key(build_id: str, url: str) -> tuple[str, str]:
    return (build_id, url)


class CacheLayer:
    def __init__(self, maxsize: int = 1024) -> None:
        self.embedding = LRU(maxsize)
        self.contents = LRU(maxsize)

    def get_contents(
        self, build_id: str, url: str, excluded: bool = False
    ) -> str | None:
        if excluded:  # D52: takedown applied after cache read
            return None
        val = self.contents.get(contents_key(build_id, url))
        return val if isinstance(val, str) else None

    def put_contents(
        self, build_id: str, url: str, text: str, degraded: bool = False
    ) -> None:
        if degraded:  # D90: degraded responses are never cached
            return
        self.contents.put(contents_key(build_id, url), text)