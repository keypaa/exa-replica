"""Shared limit status (pure domain)."""

from __future__ import annotations

from enum import Enum


class LimitStatus(str, Enum):
    OK = "ok"
    RATE = "rate"  # -> 429
    QUOTA = "quota"  # -> 429
    SUSPENDED = "suspended"
    BANNED = "banned"