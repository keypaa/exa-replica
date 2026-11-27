from pathlib import Path

from fastapi.testclient import TestClient

from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.bootstrap.composition import build_gateway
from exa_replica.domain.document import canon_v1
from exa_replica.domain.models import Hit

ROOT = Path(__file__).resolve().parent.parent


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


def _client(tmp_path):
    app = build_gateway(_StubDense(), _StubLex(), ContentStore(tmp_path))
    return TestClient(app, base_url="http://127.0.0.1")


def test_cors_preflight_refused(tmp_path):
    r = _client(tmp_path).options(
        "/search",
        headers={"Origin": "https://evil.com", "Access-Control-Request-Method": "POST"},
    )
    assert r.status_code in (403, 405)  # CORS off (D91)


def test_path_traversal():
    # dot segments removed; no traversal (D91)
    assert ".." not in canon_v1("https://x.com/../../etc/passwd")


def test_no_pickle():
    for p in (ROOT / "src").rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        assert "import pickle" not in text
        assert "pickle.loads" not in text