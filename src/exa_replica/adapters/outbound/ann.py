"""Outbound ANN / index adapters.

`DenseIndex` (R0 exact, D82) is implemented here. `StubLexicalIndex` remains a
placeholder until the BM25 adapter is wired in Task 9 (BM25Index already exists
in `bm25.py`).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from exa_replica.adapters.outbound.encoder import Embedder
from exa_replica.domain.models import Filters, Hit, Passage


class DenseIndex:
    """R0 exact GPU index (D82); CPU/numpy exact for M1 tests (bf16 at deploy)."""

    def __init__(self, embedder: Embedder, passages: Sequence[Passage]) -> None:
        self._embedder = embedder
        self._passages = list(passages)
        vecs = embedder.embed([p.text for p in self._passages])
        self._vectors = (
            np.asarray(vecs, dtype=np.float32)
            if vecs
            else np.zeros((0, 0), dtype=np.float32)
        )

    def search(
        self, query: str, filters: Filters, k: int, deadline: float
    ) -> list[Hit]:
        if self._vectors.size == 0 or deadline <= 0:
            return []
        q = np.asarray(self._embedder.embed([query])[0], dtype=np.float32)
        scores = self._vectors @ q
        order = np.argsort(-scores)[:k]
        return [
            Hit(
                doc_id=self._passages[i].doc_id,
                score=float(scores[i]),
                passage_id=self._passages[i].passage_id,
            )
            for i in order
        ]

    def stats(self) -> dict[str, float | int | str]:
        return {"vectors": int(self._vectors.shape[0])}

    def version(self) -> str:
        return "r0-exact-1"


class StubDenseIndex:
    def search(
        self, query: str, filters: Filters, k: int, deadline: float
    ) -> list[Hit]:
        raise NotImplementedError("dense index is a stub in M0; R0 lands in M1 (D82)")

    def stats(self) -> dict[str, float | int | str]:
        raise NotImplementedError("dense index is a stub in M0 (D82)")

    def version(self) -> str:
        raise NotImplementedError("dense index is a stub in M0 (D82)")


class StubLexicalIndex:
    def search(
        self, query: str, filters: Filters, k: int, deadline: float
    ) -> list[Hit]:
        raise NotImplementedError("lexical index is a stub in M0; BM25 lands in M1 (D83)")

    def stats(self) -> dict[str, float | int | str]:
        raise NotImplementedError("lexical index is a stub in M0 (D83)")

    def version(self) -> str:
        raise NotImplementedError("lexical index is a stub in M0 (D83)")