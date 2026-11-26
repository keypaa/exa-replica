from exa_replica.application.fusion import fuse
from exa_replica.domain.models import Hit


def test_rrf_k60():
    bm25 = [Hit("d1", 5.0, "p1"), Hit("d2", 3.0, "p2")]
    dense = [Hit("d1", 0.9, "p3"), Hit("d3", 0.5, "p4")]
    fused = fuse(bm25, dense)
    d1 = next(h for h in fused if h.doc_id == "d1")
    # d1 is rank 1 in both branches: 2 / (60 + 1)
    assert abs(d1.score - 2 / 61) < 1e-9
    assert fused[0].doc_id == "d1"


def test_winning_passage():
    bm25 = [Hit("d1", 5.0, "p_bm25")]
    dense = [Hit("d1", 0.9, "p_dense"), Hit("d2", 0.1, "p2")]
    fused = fuse(bm25, dense)
    d1 = next(h for h in fused if h.doc_id == "d1")
    # d1 is rank 1 in both branches → tie → smallest passage_id (D83/8)
    assert d1.passage_id == min("p_bm25", "p_dense")


def test_no_out_of_filter_result():
    # fusion only emits documents present in the (pre-filtered) inputs (D70)
    fused = fuse([Hit("d1", 5.0, "p1")], [Hit("d2", 0.9, "p2")])
    assert {h.doc_id for h in fused} <= {"d1", "d2"}