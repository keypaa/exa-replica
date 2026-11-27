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

    def encode_query(self, text):
        return self.embed([text])[0]


def test_s0_byte_exact():
    text = "First. Second. Third. Fourth."
    assert highlights(text) == highlights(text)  # deterministic (S0)
    assert highlights(text) == ["First.", "Second.", "Third."]  # pinned S0 output


def test_s1_same_sentence_choice():
    # S1 picks 3 sentences from the document; it never introduces new text (D84)
    text = "s1. s0. s2. s3. s4."
    s1 = highlights_s1(text, "guide", _FakeEmbedder())
    assert len(s1) == 3
    assert all(s in text for s in s1)
    # deterministic across runs (D63)
    assert highlights_s1(text, "guide", _FakeEmbedder()) == s1