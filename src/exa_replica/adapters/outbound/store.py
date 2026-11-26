"""Outbound store stub (M0). Implemented in M1 (D48–D50: Parquet shards + docstore)."""

from __future__ import annotations


class StubStore:
    """Placeholder for the content/doc store port (D48–D50)."""

    def put(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError("store is a stub in M0; implemented in M1 (D48–D50)")

    def get(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError("store is a stub in M0; implemented in M1 (D48–D50)")