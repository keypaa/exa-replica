import dataclasses

import pytest

from exa_replica.domain.models import Contents, Filters, Hit, Passage


def test_passage_frozen():
    p = Passage(passage_id="p1", doc_id="d1", text="hello", start=0, end=5, lang="en")
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.text = "changed"  # type: ignore[misc]


def test_hit_and_contents_frozen():
    h = Hit(doc_id="d1", score=0.5, passage_id="p1")
    with pytest.raises(dataclasses.FrozenInstanceError):
        h.score = 1.0  # type: ignore[misc]
    c = Contents(doc_id="d1", text="hello", highlights=("hello",), status="ok")
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.text = "x"  # type: ignore[misc]


def test_filters_defaults():
    f = Filters()
    assert f.domains == ()
    assert f.category is None