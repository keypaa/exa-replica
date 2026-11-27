"""S1 dense highlight selection (D84 R1).

Ranks sentences by cosine(sentence, encode_query(guiding)) (D61 query template);
adopted only if R1 passes (gain ≥2 pts IC95, latency ≤ R2, D84). **S0 is the
default** — S1 is used only when `s1_enabled` (set by the R1 decision). `lite`
forces S0. No LLM. The encoder is injected (EncoderPort); M4 tests use a fake.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from exa_replica.application.highlights import _sentences, highlights
from exa_replica.ports.encoder import EncoderPort


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def highlights_s1(
    text: str, guiding: str, embedder: EncoderPort, top_n: int = 3
) -> list[str]:
    sents = _sentences(text)
    if not sents:
        return []
    if not guiding.strip():
        return sents[:top_n]
    g = embedder.encode_query(guiding)  # D61 query template
    embs = embedder.embed(sents)
    scored = [(_cosine(e, g), i, s) for i, (s, e) in enumerate(zip(sents, embs))]
    scored.sort(key=lambda x: (-x[0], x[1]))  # tie -> smallest offset (D84)
    return [s for _, _, s in scored[:top_n]]


def select_highlights(
    text: str,
    guiding: str,
    tier: str,
    embedder: EncoderPort | None = None,
    s1_enabled: bool = False,
) -> list[str]:
    """S0 default; S1 only for auto when the R1 decision enabled it (D84)."""
    if tier == "lite" or not s1_enabled or embedder is None:
        return highlights(text)
    return highlights_s1(text, guiding, embedder)