"""Topology helpers (D89): build_id consistency across workers."""

from __future__ import annotations

from collections.abc import Sequence


def build_id_consistent(build_ids: Sequence[str]) -> bool:
    """Gateway refuses to mix two builds in one response (D89)."""
    return len(set(build_ids)) <= 1