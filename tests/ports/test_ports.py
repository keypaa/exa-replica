from exa_replica.domain.models import Filters
from exa_replica.ports.index import DenseIndex, LexicalIndex


class _FakeIndex:
    def search(self, query, filters, k, deadline):
        return []

    def stats(self):
        return {}

    def version(self):
        return "v0"


def test_dense_port_signature():
    idx: DenseIndex = _FakeIndex()
    assert idx.version() == "v0"
    assert idx.search("q", Filters(), 10, 0.0) == []
    assert idx.stats() == {}


def test_lexical_port_signature():
    idx: LexicalIndex = _FakeIndex()
    assert idx.search("q", Filters(), 10, 0.0) == []