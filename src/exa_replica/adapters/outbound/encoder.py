"""Embedding encoder (D81/D82) — provisional model injected; loaded lazily.

The provisional model is `intfloat/multilingual-e5-small` (D81, labelled
provisional). `load_embedder` imports sentence-transformers lazily so M1 tests
run without a multi-GB torch install; the real model is loaded at build/serve
time on the reference box.
"""

from __future__ import annotations

from typing import Any, Protocol

DEFAULT_MODEL = "intfloat/multilingual-e5-small"


class _Model(Protocol):
    def encode(self, texts: list[str]) -> Any: ...


class Embedder:
    def __init__(self, model: _Model) -> None:
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        raw = self._model.encode(texts)
        return [[float(x) for x in vec] for vec in raw]


def load_embedder(model_name: str = DEFAULT_MODEL, device: str = "cpu") -> Embedder:
    from sentence_transformers import SentenceTransformer

    return Embedder(SentenceTransformer(model_name, device=device))