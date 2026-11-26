from exa_replica.adapters.outbound.bm25 import BM25Index
from exa_replica.domain.models import Filters, Passage


def _p(pid: str, doc: str, text: str, lang: str = "en") -> Passage:
    return Passage(
        passage_id=pid, doc_id=doc, text=text, start=0, end=len(text), lang=lang
    )


def test_bm25_finds_relevant():
    passages = [
        _p("p1", "d1", "the cat sat on the mat"),
        _p("p2", "d2", "dogs are loyal animals"),
        _p("p3", "d3", "cats and kittens play"),
    ]
    hits = BM25Index(passages).search("cat", Filters(), 10, 1e9)
    assert hits
    assert hits[0].doc_id in ("d1", "d3")


def test_en_fr_fields():
    passages = [_p("p1", "d1", "le chat est sur le tapis", lang="fr")]
    idx = BM25Index(passages)
    hits = idx.search("chat", Filters(), 10, 1e9)
    assert hits and hits[0].doc_id == "d1"
    stats = idx.stats()
    assert "text_en" in stats and "text_fr" in stats


def test_k1_b_frozen():
    # D83: k1=1.2, b=0.75 fixed, no dev tuning.
    assert BM25Index.K1 == 1.2
    assert BM25Index.B == 0.75