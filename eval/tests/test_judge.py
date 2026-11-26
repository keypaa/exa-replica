import pytest

from eval.judge import (
    KAPPA_THRESHOLD,
    UNJUDGED_CAP,
    Judge,
    calibrate,
    cohen_kappa,
    needs_complete_judging,
    unjudged_fraction,
)


def test_kappa_threshold():
    assert cohen_kappa([1, 1, 2, 2], [1, 1, 2, 2]) == 1.0
    assert KAPPA_THRESHOLD == 0.6
    assert cohen_kappa([1, 1], [2, 2]) < KAPPA_THRESHOLD


def test_blind():
    # the judge sees only (query, doc) — never the system/source (blind, D14)
    seen: list[tuple[str, str]] = []

    def labeler(q: str, d: str) -> int:
        seen.append((q, d))
        return 1

    Judge(labeler).judge("q", "doc")
    assert seen == [("q", "doc")]


def test_calibrate():
    j = Judge(lambda q, d: 2)
    samples = [("q1", "d1", 2), ("q2", "d2", 2)]
    assert calibrate(j, samples) == 1.0


def test_unjudged_cap():
    assert UNJUDGED_CAP == 0.15
    judged = [1, 2, 3, None, 1, 2, 3, 1, 2, 3]  # 1/10 unjudged
    assert unjudged_fraction(judged) == pytest.approx(0.1)
    assert not needs_complete_judging(judged)
    assert needs_complete_judging([None] * 3 + [1] * 7)  # 30% unjudged


def test_kappa_len_mismatch():
    with pytest.raises(ValueError):
        cohen_kappa([1, 2], [1])