
from eval.highlights_ab import adopt_s1, r2_switch


def test_s1_requires_ic95():
    # negligible gain -> not adopted (D84)
    assert not adopt_s1([0.5] * 30, [0.51] * 30)
    # clear gain with IC95 lower > 0 -> adopted (>=2 pts)
    assert adopt_s1([0.5] * 30, [0.7] * 30)


def test_r2_switch():
    assert r2_switch(900.0, 800.0)  # p95 > budget -> S0 (D84)
    assert not r2_switch(500.0, 800.0)