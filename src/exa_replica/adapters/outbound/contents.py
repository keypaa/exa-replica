"""Outbound contents stub (M0). Implemented in M1 via store + highlights (D84)."""

from __future__ import annotations


class StubContentsProvider:
    """Placeholder for the `/contents` provider (store + highlights, M1)."""

    def fetch(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "contents provider is a stub in M0; implemented in M1 (D84)"
        )