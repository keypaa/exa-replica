from eval.highlight_metric import (
    kappa_uncalibrated,
    mean_precision_top10,
    success_at_3,
)


def test_success_at_3():
    assert success_at_3(["a", "b", "c", "d"], {"c"}) == 1.0
    assert success_at_3(["a", "b", "c", "d"], {"d"}) == 0.0  # not in top-3


def test_precision_all_top10():
    rel = {"a", "b"}
    ranked = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    assert mean_precision_top10(ranked, rel) == 0.2
    assert mean_precision_top10([], rel) == 0.0


def test_kappa_uncalibrated():
    assert kappa_uncalibrated(0.3)  # below 0.6 -> not used for R1 (D94)
    assert not kappa_uncalibrated(0.7)