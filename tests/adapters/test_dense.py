from exa_replica.adapters.outbound.ann import DenseIndex
from exa_replica.adapters.outbound.encoder import Embedder
from exa_replica.domain.models import Filters, Passage


class _FakeModel:
    def encode(self, texts):
        return [[float(ord(t[0]) % 7), float(len(t)), 1.0] for t in texts]


def _p(pid: str, doc: str, text: str) -> Passage:
    return Passage(
        passage_id=pid, doc_id=doc, text=text, start=0, end=len(text), lang="en"
    )


def test_r0_exact_topk():
    passages = [
        _p("p1", "d1", "apple"),
        _p("p2", "d2", "banana"),
        _p("p3", "d3", "cherry"),
    ]
    idx = DenseIndex(Embedder(_FakeModel()), passages)
    hits = idx.search("apple", Filters(), 2, 1e9)
    assert len(hits) == 2
    assert hits[0].doc_id == "d1"  # exact query match ranks first
    assert hits[0].score >= hits[1].score  # exact, sorted desc


def test_query_encode():
    emb = Embedder(_FakeModel())
    vecs = emb.embed(["hello", "world"])
    assert len(vecs) == 2
    assert all(len(v) == 3 for v in vecs)