"""S1 dense highlight selection (D84 R1).

Ranks sentences by cosine(sentence, guiding) via the encode pool; adopted only
if R1 passes (gain ≥2 pts IC95, latency ≤ R2, D84). `lite` forces S0. No LLM.
The embedder is injected; M4 tests use a fake (no GPU).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from exa_replica.application.highlights import _sentences, highlights


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def highlights_s1(
    text: str, guiding: str, embedder: object, top_n: int = 3
) -> list[str]:
    sents = _sentences(text)
    if not sents:
        return []
    if not guiding.strip():
        return sents[:top_n]
    g = embedder.embed([guiding])[0]  # type: ignore[attr-defined]
    embs = embedder.embed(sents)  # type: ignore[attr-defined]
    scored = [(_cosine(e, g), s) for s, e in zip(sents, embs)]
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [s for _, s in scored[:top_n]]


def select_highlights(
    text: str,
    guiding: str,
    tier: str,
    embedder: object,
    s1_enabled: bool = True,
) -> list[str]:
    """S0 default; S1 only for auto when enabled (D84). lite always S0."""
    if tier == "lite" or not s1_enabled:
        return highlights(text)
    return highlights_s1(text, guiding, embedder)