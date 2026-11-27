"""Rate limits + account status (D9/D10).

Token bucket (per-key QPS) + daily counter (per-key/day); separate buckets per
tier. Banned/suspended accounts are blocked before limits. 429 (rate/quota) is
distinct from 503 (queue full, S7). The clock/day are injectable for testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from exa_replica.domain.limits import LimitStatus


@dataclass
class TokenBucket:
    rate: float
    capacity: float
    tokens: float = field(default=0.0)
    last: float = field(default=0.0)

    def __post_init__(self) -> None:
        self.tokens = self.capacity

    def allow(self, now: float, n: float = 1.0) -> bool:
        self.tokens = min(
            self.capacity, self.tokens + max(0.0, now - self.last) * self.rate
        )
        self.last = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


@dataclass
class DailyCounter:
    limit: int
    count: int = 0
    day: str = ""

    def hit(self, day: str) -> bool:
        if day != self.day:
            self.day = day
            self.count = 0
        if self.count < self.limit:
            self.count += 1
            return True
        return False


def _day(now: float) -> str:
    return datetime.fromtimestamp(now, tz=UTC).strftime("%Y-%m-%d")


class RateLimiter:
    def __init__(self, limits: dict[str, tuple[float, int]]) -> None:
        self._limits = limits
        self._buckets: dict[str, TokenBucket] = {}
        self._daily: dict[str, DailyCounter] = {}

    def check(
        self, key_id: str, account_status: str, tier: str, now: float
    ) -> LimitStatus:
        if account_status == "banned":
            return LimitStatus.BANNED
        if account_status == "suspended":
            return LimitStatus.SUSPENDED
        qps, daily = self._limits[tier]
        bucket = self._buckets.setdefault(key_id, TokenBucket(qps, qps))
        if not bucket.allow(now):
            return LimitStatus.RATE
        counter = self._daily.setdefault(key_id, DailyCounter(daily))
        if not counter.hit(_day(now)):
            return LimitStatus.QUOTA
        return LimitStatus.OK