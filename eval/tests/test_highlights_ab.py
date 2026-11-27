
from eval.highlights_ab import adopt_s1, decide_s1, r2_switch


def test_s1_requires_ic95():
    # negligible gain -> not adopted (D84)
    assert not adopt_s1([0.5] * 30, [0.51] * 30)
    # clear gain with IC95 lower > 0 -> adopted (>=2 pts)
    assert adopt_s1([0.5] * 30, [0.7] * 30)
    # gain >= 2 pts but noisy (CI lower < 0) -> rejected (the IC95 check matters)
    noisy = [0.5] * 15 + [-0.44] * 15
    assert not adopt_s1([0.0] * 30, noisy)


def test_r2_switch():
    assert r2_switch(900.0, 800.0)  # p95 > budget -> S0 (D84)
    assert not r2_switch(500.0, 800.0)


def test_decide_s1():
    adopt, log = decide_s1([0.5] * 30, [0.7] * 30, 100.0, kappa=0.3, budget_ms=800)
    assert not adopt and log["reason"] == "kappa_uncalibrated"
    adopt, log = decide_s1([0.5] * 30, [0.7] * 30, 900.0, kappa=0.7, budget_ms=800)
    assert not adopt and log["reason"] == "r2_exceeded"
    adopt, log = decide_s1([0.5] * 30, [0.7] * 30, 100.0, kappa=0.7, budget_ms=800)
    assert adopt and log["decision"] == "s1"