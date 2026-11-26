import pytest
from fastapi.testclient import TestClient

from exa_replica.adapters.outbound.ann import DenseIndex
from exa_replica.adapters.outbound.bm25 import BM25Index
from exa_replica.adapters.outbound.encoder import Embedder
from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.application.chunker import chunk
from exa_replica.bootstrap.composition import build_gateway
from exa_replica.domain.document import Document


class _FakeModel:
    def encode(self, texts):
        return [[1.0, 1.0, 1.0] for _ in texts]


@pytest.fixture
def client(tmp_path):
    store = ContentStore(tmp_path)
    doc = Document(
        url_canonical="https://x.com/a",
        generation="G",
        url_original="",
        warc_ref="",
        crawled_at="",
        title=None,
        published_date=None,
        author=None,
        lang="en",
        text_canonical="the cat sat on the mat.",
        content_hash="h",
        extractor_version="t",
    )
    ch = chunk(doc)
    store.put(doc, ch.passages)
    app = build_gateway(
        DenseIndex(Embedder(_FakeModel()), list(ch.passages)),
        BM25Index(list(ch.passages)),
        store,
    )
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c


def test_mcp_tools(client):
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "t", "version": "0"},
        },
    }
    client.post("/mcp", json=init, headers={"Accept": "application/json, text/event-stream"})
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        headers={"Accept": "application/json, text/event-stream"},
    )
    assert r.status_code == 200
    names = [t["name"] for t in r.json()["result"]["tools"]]
    assert "web_search_exa" in names
    assert "web_fetch_exa" in names