from eval.judge import KAPPA_THRESHOLD, Judge, calibrate, cohen_kappa


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