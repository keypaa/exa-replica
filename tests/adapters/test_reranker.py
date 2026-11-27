from exa_replica.adapters.outbound.reranker import Reranker, _sigmoid
from exa_replica.domain.models import Hit


class _FakeCE:
    def predict(self, pairs):
        # score by passage length (deterministic, no model)
        return [float(len(t)) for _, t in pairs]


def test_score_sigmoid():
    assert 0.0 < _sigmoid(0.0) < 1.0
    assert _sigmoid(100.0) > 0.99
    assert _sigmoid(-100.0) < 0.01


def test_rerank_changes_order():
    r = Reranker(_FakeCE())
    hits = [
        (Hit("d1", 0.9, "p1"), "short"),
        (Hit("d2", 0.1, "p2"), "a much longer passage text that scores higher"),
    ]
    reranked, degraded = r.rerank("q", hits, deadline=1e9)
    assert not degraded
    assert reranked[0].doc_id == "d2"  # re-ordered by the cross-encoder
    assert reranked[0].score == 0.1  # original hit preserved (not the sigmoid)


def test_rerank_timeout_fusion():
    r = Reranker(_FakeCE())
    hits = [(Hit("d1", 0.5, "p1"), "x"), (Hit("d2", 0.4, "p2"), "y")]
    reranked, degraded = r.rerank("q", hits, deadline=0.0)  # expired
    assert degraded  # >800ms / deadline -> fusion order + degraded (D67)
    assert [h.doc_id for h in reranked] == ["d1", "d2"]  # fusion order kept


def test_rerank_slow_model():
    import time

    class _SlowCE:
        def predict(self, pairs):
            time.sleep(0.05)
            return [1.0 for _ in pairs]

    r = Reranker(_SlowCE(), timeout_s=0.01)  # 10ms budget
    hits = [(Hit("d1", 0.5, "p1"), "x")]
    reranked, degraded = r.rerank("q", hits, deadline=1e9)
    assert degraded  # scoring overran the budget -> fusion order (D67)
    assert reranked[0].doc_id == "d1"


def test_rerank_nan_degraded():
    class _NanCE:
        def predict(self, pairs):
            return [float("nan") for _ in pairs]

    r = Reranker(_NanCE())
    hits = [(Hit("d1", 0.5, "p1"), "x")]
    reranked, degraded = r.rerank("q", hits, deadline=1e9)
    assert degraded  # NaN/inf -> fusion order + degraded (D67)
    assert reranked[0].doc_id == "d1"