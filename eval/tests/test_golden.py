from eval.golden.build import build_golden, split_dev_test


def _recs(n: int) -> list[dict]:
    return [
        {"query": f"q{i}", "cluster": f"c{i}", "objective": f"o{i}", "relevance": {}}
        for i in range(n)
    ]


def test_hash_split_deterministic():
    a = split_dev_test(_recs(40), 10)
    b = split_dev_test(_recs(40), 10)
    assert [r["query"] for r in a[0]] == [r["query"] for r in b[0]]


def test_cluster_dedup():
    recs = [
        {"query": "q1", "cluster": "c1", "relevance": {}},
        {"query": "q1b", "cluster": "c1", "relevance": {}},  # dup cluster
        {"query": "q2", "cluster": "c2", "relevance": {}},
    ]
    dev, test = split_dev_test(recs, 10)
    # one record per cluster
    assert len(dev) + len(test) == 2


def test_test_split_untouched():
    # M2 builds/holds out the test split but must not read it (D14).
    gs = build_golden(_recs(40), 10)
    assert gs.test  # held out, not consumed in M2
    assert gs.provisional is True


def test_provisional_label():
    assert build_golden(_recs(10), 5).provisional is True