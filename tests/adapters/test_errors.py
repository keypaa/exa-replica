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


class _FakeAuth:
    def __init__(self, status="active"):
        self._status = status

    def authenticate(self, key):
        return "acc1" if key == "exa_good" else None

    def account_status(self, account):
        return self._status


def _client(tmp_path, auth=None, limiter=None):
    app = build_gateway(
        _StubDense(), _StubLex(), ContentStore(tmp_path), auth=auth, limiter=limiter
    )
    return TestClient(app, base_url="http://127.0.0.1")


def test_429_rate_limited(tmp_path):
    limiter = RateLimiter({"lite": (1.0, 150)})
    c = _client(tmp_path, auth=_FakeAuth(), limiter=limiter)
    h = {"x-api-key": "exa_good"}
    assert c.post("/search", json={"query": "x", "type": "lite"}, headers=h).status_code == 200
    r2 = c.post("/search", json={"query": "x", "type": "lite"}, headers=h)
    assert r2.status_code == 429
    assert "Retry-After" in r2.headers


def test_invalid_key_401(tmp_path):
    c = _client(tmp_path, auth=_FakeAuth())
    r = c.post("/search", json={"query": "x", "type": "lite"}, headers={"x-api-key": "bad"})
    assert r.status_code == 401
    assert "X-Request-Id" in r.headers


def test_413(tmp_path):
    c = _client(tmp_path)
    r = c.post("/search", content=b"x" * 2_000_000, headers={"content-type": "application/json"})
    assert r.status_code == 413


def test_415(tmp_path):
    c = _client(tmp_path)
    r = c.post("/search", content=b"notjson", headers={"content-type": "text/plain"})
    assert r.status_code == 415


def test_409(tmp_path):
    c = _client(tmp_path)
    r = c.post(
        "/search",
        json={"query": "x", "type": "lite"},
        headers={"X-Index-Version": "bogus"},
    )
    assert r.status_code == 409