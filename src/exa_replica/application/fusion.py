"""Reciprocal Rank Fusion (D81/D83).

RRF with k=60 ranks **documents**. The winning passage for a document is the
passage of the branch that ranks it higher; ties break to the smallest
`passage_id` (D83/8). Fusion only emits documents present in the inputs — filters
are applied before fusion (D70), so no out-of-filter result can appear.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from exa_replica.domain.models import Hit

RRF_K = 60


@dataclass(frozen=True, slots=True)
class DocHit:
    doc_id: str
    score: float
    passage_id: str


def _ranks(hits: Sequence[Hit]) -> dict[str, tuple[int, str]]:
    # Keep the best (minimum) rank per doc and its passage (D83/2).
    out: dict[str, tuple[int, str]] = {}
    for i, h in enumerate(hits):
        rank = i + 1
        if h.doc_id not in out or rank < out[h.doc_id][0]:
            out[h.doc_id] = (rank, h.passage_id)
    return out


def fuse(bm25_hits: Sequence[Hit], dense_hits: Sequence[Hit]) -> list[DocHit]:
    bm = _ranks(bm25_hits)
    dn = _ranks(dense_hits)
    out: list[DocHit] = []
    for doc in set(bm) | set(dn):
        score = 0.0
        candidates: list[tuple[int, str]] = []
        if doc in bm:
            rank, pid = bm[doc]
            score += 1.0 / (RRF_K + rank)
            candidates.append((rank, pid))
        if doc in dn:
            rank, pid = dn[doc]
            score += 1.0 / (RRF_K + rank)
            candidates.append((rank, pid))
        candidates.sort(key=lambda t: (t[0], t[1]))
        out.append(DocHit(doc, score, candidates[0][1]))
    out.sort(key=lambda h: (-h.score, h.doc_id))
    return out