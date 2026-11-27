"""Rate-limiter port (D85/D95): the inbound layer depends on this, not the adapter."""

from __future__ import annotations

from typing import Protocol

from exa_replica.domain.limits import LimitStatus


class RateLimiterPort(Protocol):
    def check(
        self,
        key_id: str,
        account_status: str,
        tier: str,
        now: float,
        day: str | None = None,
    ) -> LimitStatus: ...