"""Gate 2 (keyed mode, D3–D11): surface + keys + limits + bans + errors."""

from typing import ClassVar

from fastapi.testclient import TestClient

from exa_replica.adapters.outbound.pg.limits import RateLimiter
from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.bootstrap.composition import build_gateway
from exa_replica.domain.models import Hit


class _StubDense:
    def search(self, q, f, k, d):
        return [Hit("d1", 0.9, "p1")]

    def stats(self):
        return {}

    def version(self):
        return "v0"


class _StubLex:
    def search(self, q, f, k, d):
        return []

    def stats(self):
        return {}

    def version(self):
        return "v0"


class _Auth:
    _accounts: ClassVar[dict[str, str]] = {"exa_good": "acc1", "exa_banned": "acc2"}

    def authenticate(self, key):
        return self._accounts.get(key)

    def account_status(self, account):
        return "banned" if account == "acc2" else "active"


def test_gate2_keyed_mode(tmp_path):
    limiter = RateLimiter({"lite": (10.0, 150), "auto": (5.0, 100)})
    app = build_gateway(
        _StubDense(), _StubLex(), ContentStore(tmp_path), auth=_Auth(), limiter=limiter
    )
    with TestClient(app, base_url="http://127.0.0.1") as c:
        body = {"query": "x", "type": "lite"}
        assert c.post("/search", json=body).status_code == 401  # no key
        assert c.post("/search", json=body, headers={"x-api-key": "bad"}).status_code == 401
        assert c.post("/search", json=body, headers={"x-api-key": "exa_good"}).status_code == 200
        assert c.post("/search", json=body, headers={"x-api-key": "exa_banned"}).status_code == 403
        # envelope + request id present on an error
        r = c.post("/search", json=body, headers={"x-api-key": "bad"})
        assert "X-Request-Id" in r.headers
        assert "error" in r.json()