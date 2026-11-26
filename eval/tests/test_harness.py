from eval.harness import run_eval
from eval.metrics import ndcg_at_k, recall_at_k


def test_recall_at_k():
    retrieved = ["a", "b", "c", "d"]
    relevant = {"a", "c"}
    assert recall_at_k(retrieved, relevant, 2) == 0.5
    assert recall_at_k(retrieved, relevant, 4) == 1.0
    assert recall_at_k(retrieved, set(), 4) == 0.0


def test_ndcg10():
    relevance = {"a": 3.0, "b": 0.0}
    assert abs(ndcg_at_k(["a", "b"], relevance, 10) - 1.0) < 1e-9
    assert ndcg_at_k(["b", "a"], relevance, 10) < 1.0


def test_run_eval():
    def system(_q):
        return ["a", "b"]

    r = run_eval(system, [{"query": "x", "relevant": ["a"]}])
    assert r.n == 1
    assert r.recall_at_10 == 1.0
    assert r.ndcg_at_10 == 1.0


def test_run_eval_unjudged_graceful():
    # an unjudged query (no `relevant`) must not KeyError (evidence-blocked set)
    def system(_q):
        return ["a"]

    r = run_eval(system, [{"query": "x"}])
    assert r.n == 1