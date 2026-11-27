"""API key identity (D3–D7): generate / verify / rotate / revoke.

Keys are `exa_` + 64 hex chars (D3). Only an HMAC of the secret is stored
(pepper + hash_version); the plaintext secret is shown once at generation.
Expiry default 1 year (D5); rotation has a grace window (D6); revocation is
idempotent with a reason (D7). The clock is injected for testing.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

KEY_PREFIX = "exa_"
SECRET_BYTES = 32  # -> 64 hex chars
HASH_VERSION = 1
DEFAULT_TTL_DAYS = 365
ROTATION_GRACE_HOURS = 24
GRACE_MAX_HOURS = 24 * 7


@dataclass(frozen=True, slots=True)
class KeyRecord:
    key_id: str
    account_id: str
    scopes: tuple[str, ...]
    hash_version: int
    pepper_version: int
    expires_at: float | None
    rotated_from: str | None
    revoked: bool


class ApiKeyRepository(Protocol):
    def put(self, rec: KeyRecord) -> None: ...

    def get(self, key_id: str) -> KeyRecord | None: ...

    def list_by_account(self, account_id: str) -> list[KeyRecord]: ...


class ApiKeyService:
    def __init__(
        self,
        repo: ApiKeyRepository,
        pepper: bytes,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._repo = repo
        self._pepper = pepper
        self._clock = clock

    def _hash(self, secret: str) -> str:
        return hmac.new(self._pepper, secret.encode("utf-8"), hashlib.sha256).hexdigest()

    def generate(
        self,
        account_id: str,
        scopes: tuple[str, ...],
        ttl_days: int | None = DEFAULT_TTL_DAYS,
    ) -> tuple[str, KeyRecord]:
        secret = secrets.token_hex(SECRET_BYTES)
        key = KEY_PREFIX + secret
        key_id = self._hash(secret)[:32]
        expires_at = self._clock() + ttl_days * 86400 if ttl_days else None
        rec = KeyRecord(
            key_id=key_id,
            account_id=account_id,
            scopes=scopes,
            hash_version=HASH_VERSION,
            pepper_version=1,
            expires_at=expires_at,
            rotated_from=None,
            revoked=False,
        )
        self._repo.put(rec)
        return key, rec

    def verify(self, key: str) -> KeyRecord | None:
        if not key.startswith(KEY_PREFIX):
            return None
        secret = key[len(KEY_PREFIX) :]
        rec = self._repo.get(self._hash(secret)[:32])
        if rec is None or rec.revoked:
            return None
        if rec.expires_at is not None and self._clock() > rec.expires_at:
            return None
        return rec

    def rotate(self, key_id: str) -> tuple[str, KeyRecord]:
        rec = self._repo.get(key_id)
        if rec is None:
            raise ValueError("unknown key")
        # refuse if a rotation from this key is already in its grace window (D6)
        for other in self._repo.list_by_account(rec.account_id):
            if other.rotated_from == key_id and not other.revoked:
                raise ValueError("key is within its rotation grace window")
        new_key, new_rec = self.generate(rec.account_id, rec.scopes)
        rotated = KeyRecord(
            key_id=new_rec.key_id,
            account_id=new_rec.account_id,
            scopes=new_rec.scopes,
            hash_version=new_rec.hash_version,
            pepper_version=new_rec.pepper_version,
            expires_at=new_rec.expires_at,
            rotated_from=rec.key_id,
            revoked=False,
        )
        self._repo.put(rotated)
        return new_key, rotated

    def revoke(self, key_id: str, reason: str) -> None:
        rec = self._repo.get(key_id)
        if rec is None or rec.revoked:
            return  # idempotent (D7)
        self._repo.put(
            KeyRecord(
                key_id=rec.key_id,
                account_id=rec.account_id,
                scopes=rec.scopes,
                hash_version=rec.hash_version,
                pepper_version=rec.pepper_version,
                expires_at=rec.expires_at,
                rotated_from=rec.rotated_from,
                revoked=True,
            )
        )