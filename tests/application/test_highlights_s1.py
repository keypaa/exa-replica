from typing import ClassVar

from exa_replica.application.highlights_s1 import highlights_s1, select_highlights
from exa_replica.domain.models import Hit  # noqa: F401


class _FakeEmbedder:
    """Embeds by a fixed vector per text (cosine-rankable)."""

    _V: ClassVar[dict[str, list[float]]] = {
        "guide": [1.0, 0.0],
        "s0.": [0.9, 0.1],
        "s1.": [0.0, 1.0],
        "s2.": [0.7, 0.7],
    }

    def embed(self, texts):
        return [self._V.get(t, [0.5, 0.5]) for t in texts]

    def encode_query(self, text):
        return self.embed([text])[0]


def test_s1_ranks_by_cosine():
    text = "s1. s0. s2."
    out = highlights_s1(text, "guide", _FakeEmbedder(), top_n=3)
    # highest cosine to guide ([1,0]) is s0, then s2, then s1
    assert out[0] == "s0."
    assert out[1] == "s2."
    assert out[2] == "s1."


def test_lite_forces_s0():
    text = "s1. s0. s2."
    # lite -> S0 (first sentences), never S1
    out = select_highlights(text, "guide", tier="lite", embedder=_FakeEmbedder(), s1_enabled=True)
    assert out[0] == "s1."  # first sentence (S0 order)