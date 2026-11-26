"""Outbound ANN / index stubs (M0).

`StubDenseIndex` (R0 exact GPU, D82) and `StubLexicalIndex` (BM25/Tantivy, D83)
are placeholders; both are implemented in M1. The lexical stub lives here only
because `bm25.py` lands in M1.
"""

from __future__ import annotations

from exa_replica.domain.models import Filters, Hit


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