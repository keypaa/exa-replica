"""Encoder port (D85/D95): embed + query-encode (D61 query template)."""

from __future__ import annotations

from typing import Protocol


class EncoderPort(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def encode_query(self, text: str) -> list[float]: ...