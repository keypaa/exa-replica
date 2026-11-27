"""Generation switch (D68): atomic; 2×V_gpu peak or short dense outage.

`plan_switch` decides the mode from the VRAM budget; `apply_switch` is the atomic
activation (the new build becomes active; the old is retired). Mono-GPU: build and
serving never run simultaneously (D68).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SwitchPlan:
    mode: str  # "2x_peak" | "short_outage"
    new_build_id: str


def plan_switch(
    current_build: str, new_build: str, v_gpu_peak_gb: float, budget_gb: float
) -> SwitchPlan:
    mode = "2x_peak" if 2 * v_gpu_peak_gb <= budget_gb else "short_outage"
    return SwitchPlan(mode, new_build)


def apply_switch(current_build: str, new_build: str) -> str:
    """Atomic activation: returns the new active build_id (D68)."""
    return new_build