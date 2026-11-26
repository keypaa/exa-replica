"""Offline eval harness (§1.5/D35).

`system(query) -> list[str]` (ranked doc ids). `queries` are dicts with `query`,
`relevant` (set of ids) and optional `relevance` (id -> gain). Returns a `Report`
with mean recall@10, nDCG@10, MRR. Dev split only (D14).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from eval.metrics import mrr, ndcg_at_k, recall_at_k


@dataclass(frozen=True, slots=True)
class Report:
    recall_at_10: float
    ndcg_at_10: float
    mrr: float
    n: int


def run_eval(
    system: Callable[[str], list[str]], queries: Sequence[dict[str, Any]]
) -> Report:
    recalls: list[float] = []
    ndcgs: list[float] = []
    mrrs: list[float] = []
    for q in queries:
        ranked = system(q["query"])
        relevant = set(q.get("relevant") or ())
        relevance = q.get("relevance") or {d: 1.0 for d in relevant}
        recalls.append(recall_at_k(ranked, relevant, 10))
        ndcgs.append(ndcg_at_k(ranked, relevance, 10))
        mrrs.append(mrr(ranked, relevant))
    n = len(queries)
    if n == 0:
        return Report(0.0, 0.0, 0.0, 0)
    return Report(
        sum(recalls) / n, sum(ndcgs) / n, sum(mrrs) / n, n
    )