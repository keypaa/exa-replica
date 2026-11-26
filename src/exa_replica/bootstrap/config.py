"""Typed, immutable settings loaded from env, validated at startup (D92).

The process refuses to start on invalid config: constructing `Settings` raises
`ValidationError`, and `build_default_gateway` constructs it eagerly.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_VALID_TIERS = ("lite", "auto")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EXA_REPLICA_", extra="forbid")

    tier: str = "auto"
    host: str = "127.0.0.1"
    port: int = 8080
    data_dir: str = ".exa-replica-data"

    @field_validator("tier")
    @classmethod
    def _validate_tier(cls, v: str) -> str:
        if v not in _VALID_TIERS:
            raise ValueError(
                f"tier must be one of {_VALID_TIERS} (deep is out of v1, D15/D18)"
            )
        return v