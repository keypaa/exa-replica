"""Static tier plans (D86). v1 uses one fixed plan per tier; a real DAG is LATER.

Canonical stage order is the D66 order:
query encode → BM25 ∥ dense → fusion (RRF) → rerank → contents → highlights.
"""

from __future__ import annotations

from dataclasses import dataclass

# D66 execution order. `encode` precedes the two retrieval branches, which run
# in parallel; `fusion` merges them; the rest follow.
STAGE_ORDER: tuple[str, ...] = (
    "encode",
    "bm25",
    "dense",
    "fusion",
    "rerank",
    "contents",
    "highlights",
)

# v1 tiers (D8/D15/D18): deep is out of v1 and rejected.
_LITE = ("encode", "bm25", "dense", "fusion", "contents", "highlights")
_AUTO = ("encode", "bm25", "dense", "fusion", "rerank", "contents", "highlights")


@dataclass(frozen=True, slots=True)
class TierPlan:
    """The ordered set of stages a tier executes (D86)."""

    tier: str
    stages: tuple[str, ...]


_PLANS: dict[str, TierPlan] = {
    "lite": TierPlan(tier="lite", stages=_LITE),
    "auto": TierPlan(tier="auto", stages=_AUTO),
}


def plan_for(tier: str) -> TierPlan:
    """Return the static plan for `tier`; reject unknown/deep tiers (D15/D18)."""
    try:
        return _PLANS[tier]
    except KeyError:
        raise ValueError(f"unknown tier: {tier!r} (v1 supports lite|auto)") from None