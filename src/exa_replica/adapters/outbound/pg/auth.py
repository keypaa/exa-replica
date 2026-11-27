"""Authenticator adapter (D8/D24): bridges ApiKeyService + account status.

`authenticate` returns the account_id for a valid key (or None → uniform 401);
`account_status` reports active/suspended/banned. The Postgres repo is the deploy
implementation; M3 uses an in-memory repo.
"""

from __future__ import annotations

from typing import Protocol

from exa_replica.adapters.outbound.pg.keys import ApiKeyService


class AccountRepository(Protocol):
    def status(self, account_id: str) -> str: ...


class InMemoryAccounts:
    def __init__(self) -> None:
        self._status: dict[str, str] = {}

    def set(self, account_id: str, status: str) -> None:
        self._status[account_id] = status

    def status(self, account_id: str) -> str:
        return self._status.get(account_id, "active")


class PgAuthenticator:
    def __init__(self, keys: ApiKeyService, accounts: AccountRepository) -> None:
        self._keys = keys
        self._accounts = accounts

    def authenticate(self, key: str) -> str | None:
        rec = self._keys.verify(key)
        return rec.account_id if rec else None

    def account_status(self, account: str) -> str:
        return self._accounts.status(account)