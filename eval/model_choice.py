"""D81 provisional model choice (filters 0–1).

Step 1 filters: license (D57: Apache-2.0/MIT) and language (D58: EN+FR). The
result is **provisional** (labelled) and cannot enter a frozen spec (D81);
throughput/quality filters (D65/D66/D73) run during evidence on the reference box.
FR is required for the model, but FR *quality* is diagnostic, not gating (D93).
"""

from __future__ import annotations

from dataclasses import dataclass

PROVISIONAL = True
_ALLOWED_LICENSES = {"apache-2.0", "mit"}


@dataclass(frozen=True, slots=True)
class Candidate:
    name: str
    license: str
    languages: tuple[str, ...]
    params_m: int
    dim: int


def license_filter(cands: list[Candidate]) -> list[Candidate]:
    return [c for c in cands if c.license.lower() in _ALLOWED_LICENSES]


def language_filter(
    cands: list[Candidate], required: tuple[str, ...] = ("en", "fr")
) -> list[Candidate]:
    return [c for c in cands if all(l in c.languages for l in required)]


def select_provisional(cands: list[Candidate]) -> Candidate:
    """D81 step 1: smallest admitted candidate as the provisional default."""
    admitted = language_filter(license_filter(cands))
    if not admitted:
        raise ValueError("no candidate passes D81 step 1 (license + EN/FR)")
    return min(admitted, key=lambda c: c.params_m)