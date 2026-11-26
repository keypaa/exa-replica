from fastapi.testclient import TestClient

from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.bootstrap.composition import build_gateway
from exa_replica.domain.models import Hit


class _StubDense:
    def search(self, query, filters, k, deadline):
        return [Hit("d1", 0.9, "p1")]

    def stats(self):
        return {}

    def version(self):
        return "v0"


class _StubLexical:
    def search(self, query, filters, k, deadline):
        return []

    def stats(self):
        return {}

    def version(self):
        return "v0"


def test_gateway_serves_search_and_mcp(tmp_path):
    app = build_gateway(_StubDense(), _StubLexical(), ContentStore(tmp_path))

    # Run as a context manager so the MCP session manager's lifespan starts.
    with TestClient(app, base_url="http://127.0.0.1") as client:
        r = client.post(
            "/search", json={"query": "hello", "type": "auto", "numResults": 10}
        )
        assert r.status_code == 200
        assert "results" in r.json()

        init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "0"},
            },
        }
        rm = client.post(
            "/mcp",
            json=init,
            headers={"Accept": "application/json, text/event-stream"},
        )
        assert rm.status_code == 200
        assert "result" in rm.json()