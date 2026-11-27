"""Gate helpers (D97): Gate 4 pilot is recorded, never blocking."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from eval.harness import Report, run_eval


@dataclass(frozen=True, slots=True)
class PilotResult:
    report: Report
    blocking: bool = False  # D97: the Gate 4 pilot never blocks


def run_pilot(
    system: Callable[[str], list[str]], queries: Sequence[dict]
) -> PilotResult:
    return PilotResult(run_eval(system, queries), blocking=False)