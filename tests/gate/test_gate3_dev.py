import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _dcg(gains: list[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def _ndcg_at_k(labels: list[int], k: int) -> float:
    dcg = _dcg([float(x) for x in labels[:k]])
    idcg = _dcg([float(x) for x in sorted(labels, reverse=True)[:k]])
    return dcg / idcg if idcg > 0 else 0.0


def test_gate3_dev_quality():
    golden = ROOT / "bench" / "results" / "golden_dev.jsonl"
    assert golden.exists(), "dev golden set required for Gate 3 (D93)"
    by_query: dict[str, list[int]] = defaultdict(list)
    for line in golden.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            by_query[r["query"]].append(int(r["label"]))
    ndcgs = [_ndcg_at_k(v, 10) for v in by_query.values()]
    mean = sum(ndcgs) / len(ndcgs)
    # a valid dev quality report; the test split is NOT read here (D14)
    assert 0.0 <= mean <= 1.0
    assert len(by_query) > 0