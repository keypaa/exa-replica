"""Outbound encoder stub (M0). Implemented in M1 (D81/D82: provisional model, bf16)."""

from __future__ import annotations


class StubEncoder:
    """Placeholder for the embedding encoder (D81/D82)."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("encoder is a stub in M0; implemented in M1 (D81/D82)")