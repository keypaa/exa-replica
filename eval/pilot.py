"""Dev pilot σ (D93/D14).

σ is computed on **paired** per-query differences (hybrid − BM25), never on raw
scores, for the BM25-floor margin. Runs on the dev split only; the test split is
never read in M2 (D14).
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Sequence

from eval.metrics import recall_at_k


def paired_diffs(bm25: Sequence[float], hybrid: Sequence[float]) -> list[float]:
    return [h - b for b, h in zip(bm25, hybrid)]


def _per_query_recall(system: Callable[[str], list[str]], queries: Sequence[dict]) -> list[float]:
    out: list[float] = []
    for q in queries:
        ranked = system(q["query"])
        out.append(recall_at_k(ranked, set(q["relevant"]), 10))
    return out


def pilot(
    bm25_system: Callable[[str], list[str]],
    hybrid_system: Callable[[str], list[str]],
    dev_queries: Sequence[dict],
    metric: Callable[[Callable[[str], list[str]], Sequence[dict]], list[float]] = _per_query_recall,
) -> dict:
    b = metric(bm25_system, dev_queries)
    h = metric(hybrid_system, dev_queries)
    diffs = paired_diffs(b, h)
    sigma = statistics.pstdev(diffs) if len(diffs) > 1 else 0.0
    return {"sigma": sigma, "n": len(diffs), "paired": True, "diffs": diffs}