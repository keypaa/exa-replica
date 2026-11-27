from typing import ClassVar

from exa_replica.application.highlights import highlights
from exa_replica.application.highlights_s1 import highlights_s1


class _FakeEmbedder:
    _V: ClassVar[dict[str, list[float]]] = {
        "guide": [1.0, 0.0],
        "s0.": [0.9, 0.1],
        "s1.": [0.0, 1.0],
        "s2.": [0.7, 0.7],
    }

    def embed(self, texts):
        return [self._V.get(t, [0.5, 0.5]) for t in texts]


def test_s0_byte_exact():
    text = "First. Second. Third. Fourth."
    assert highlights(text) == highlights(text)  # deterministic (S0)
    assert highlights(text) == ["First.", "Second.", "Third."]  # pinned S0 output


def test_s1_same_sentence_choice():
    # S1 reorders the SAME sentences S0 chose; it never introduces new text (D84)
    text = "s1. s0. s2."
    s0 = set(highlights(text))
    s1 = set(highlights_s1(text, "guide", _FakeEmbedder()))
    assert s1 <= s0
    assert s1  # non-empty