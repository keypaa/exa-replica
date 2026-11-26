"""Golden set builder (D93) — provisional.

The real D93 set (100 EN dev + 100 test, judged; FR 100 diagnostic) needs a query
source + judge labels (evidence, RTX/LLM). This builder implements the *procedure*
(cluster dedup, hash split, strata) and is labelled provisional; the full judged
set is evidence-blocked. M2 consumes dev only; the test split is held out (D14).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoldenSet:
    dev: list[dict]
    test: list[dict]
    provisional: bool


def _cluster_key(rec: dict) -> str:
    return rec.get("cluster") or rec["query"]


def split_dev_test(
    records: list[dict], n_dev: int, seed: str = "exa-replica-v1"
) -> tuple[list[dict], list[dict]]:
    # cluster dedup: keep one record per cluster (near-dup control, D93).
    seen: dict[str, dict] = {}
    for r in records:
        seen.setdefault(_cluster_key(r), r)
    dev: list[dict] = []
    test: list[dict] = []
    for cluster in sorted(seen):
        h = int(hashlib.sha256(f"{seed}:{cluster}".encode()).hexdigest(), 16) % 100
        (dev if h < 50 else test).append(seen[cluster])
    return dev[:n_dev], test


def build_golden(
    records: list[dict],
    n_dev: int = 100,
    seed: str = "exa-replica-v1",
    provisional: bool = True,
) -> GoldenSet:
    dev, test = split_dev_test(records, n_dev, seed)
    return GoldenSet(dev, test, provisional)