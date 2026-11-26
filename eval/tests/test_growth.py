import math

from eval.growth import n_test


def test_growth_formula():
    sigma, h = 0.25, 0.05
    raw = math.ceil((1.96 * sigma / h) ** 2)
    expected = math.ceil(max(100, raw) / 50) * 50
    assert n_test(sigma, h) == min(expected, 400)


def test_cap_400():
    assert n_test(10.0, 0.01) == 400


def test_floor_100():
    assert n_test(0.0, 0.05) == 100