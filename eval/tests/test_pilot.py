import pytest

from eval.pilot import paired_diffs, pilot


def test_pilot_uses_paired_diffs():
    # paired diffs = hybrid - bm25 per query (D93/D14), not raw scores
    assert paired_diffs([0.5, 0.5, 0.5], [0.6, 0.4, 0.5]) == pytest.approx([0.1, -0.1, 0.0])


def test_pilot_no_test():
    # pilot runs on the dev set only; no test split is read (D14)
    dev = [{"query": "q", "relevant": ["a"]}]

    def system(_q):
        return ["a"]

    r = pilot(system, system, dev)
    assert r["n"] == 1
    assert r["paired"] is True