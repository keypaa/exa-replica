"""D81 quality eval (evidence, D35): nDCG@10 / recall@10 / MRR from judged candidates.

Reads golden_dev.jsonl (candidates in system-ranked order + LLM label) and
computes per-query ranking metrics for the provisional model (D81 step 3). No
corpus or GPU needed.

Run: python bench/eval_quality.py
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path


def _dcg(gains: list[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(labels: list[int], k: int) -> float:
    dcg = _dcg([float(x) for x in labels[:k]])
    idcg = _dcg([float(x) for x in sorted(labels, reverse=True)[:k]])
    return dcg / idcg if idcg > 0 else 0.0


def recall_at_k(labels: list[int], k: int) -> float:
    rel = [i for i, x in enumerate(labels) if x > 0]
    if not rel:
        return 0.0
    return sum(1 for i in rel if i < k) / len(rel)


def mrr(labels: list[int]) -> float:
    for i, x in enumerate(labels):
        if x > 0:
            return 1.0 / (i + 1)
    return 0.0


def main() -> None:
    path = Path("bench/results/golden_dev.jsonl")
    by_query: dict[str, list[int]] = defaultdict(list)
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_query[r["query"]].append(int(r["label"]))

    ndcgs, recalls, mrrs = [], [], []
    for labels in by_query.values():
        ndcgs.append(ndcg_at_k(labels, 10))
        recalls.append(recall_at_k(labels, 10))
        mrrs.append(mrr(labels))
    n = len(by_query)
    report = {
        "n_queries": n,
        "n_candidates": sum(len(v) for v in by_query.values()),
        "ndcg_at_10_mean": round(sum(ndcgs) / n, 4) if n else 0.0,
        "recall_at_10_mean": round(sum(recalls) / n, 4) if n else 0.0,
        "mrr_mean": round(sum(mrrs) / n, 4) if n else 0.0,
        "queries_with_relevant": sum(1 for v in by_query.values() if any(x > 0 for x in v)),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()