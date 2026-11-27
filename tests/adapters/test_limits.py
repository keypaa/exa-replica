from exa_replica.adapters.outbound.pg.limits import (
    DailyCounter,
    LimitStatus,
    RateLimiter,
    TokenBucket,
)


def test_token_bucket():
    tb = TokenBucket(rate=10.0, capacity=10.0)
    assert all(tb.allow(0.0) for _ in range(10))
    assert not tb.allow(0.0)  # empty (D9)
    assert tb.allow(1.0)  # refilled after 1s at 10/s


def test_daily_counter():
    dc = DailyCounter(limit=150)
    assert all(dc.hit("2026-11-27") for _ in range(150))
    assert not dc.hit("2026-11-27")  # over daily quota (D9)
    assert dc.hit("2026-11-28")  # new day resets


def test_ban_blocks():
    rl = RateLimiter(limits={"lite": (10.0, 150), "auto": (5.0, 100)})
    assert rl.check("k1", "banned", "lite", 0.0) == LimitStatus.BANNED
    assert rl.check("k2", "suspended", "lite", 0.0) == LimitStatus.SUSPENDED
    assert rl.check("k3", "active", "lite", 0.0) == LimitStatus.OK


def test_429_vs_503():
    rl = RateLimiter(limits={"lite": (1.0, 150)})
    assert rl.check("k", "active", "lite", 0.0) == LimitStatus.OK
    # bucket empty -> rate limited (429), not 503 (queue full is S7)
    assert rl.check("k", "active", "lite", 0.0) == LimitStatus.RATE