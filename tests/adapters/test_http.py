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
        return [[float(ord(t[0]) % 7), float(len(t)), 1.0] for t in texts]


def _doc(url: str, text: str, exclusion: str = "none") -> Document:
    return Document(
        url_canonical=url,
        generation="G",
        url_original=url,
        warc_ref="",
        crawled_at="",
        title=None,
        published_date=None,
        author=None,
        lang="en",
        text_canonical=text,
        content_hash="h",
        extractor_version="t",
        exclusion=exclusion,
    )


@pytest.fixture
def client(tmp_path):
    store = ContentStore(tmp_path)
    docs = [
        _doc("https://x.com/a", "the cat sat on the mat. It was warm today."),
        _doc("https://x.com/b", "dogs are loyal animals. They bark loudly."),
        _doc("https://x.com/c", "taken down secret content here.", exclusion="takedown"),
    ]
    passages = []
    for d in docs:
        ch = chunk(d)
        store.put(d, ch.passages)
        passages.extend(ch.passages)
    dense = DenseIndex(Embedder(_FakeModel()), passages)
    lexical = BM25Index(passages)
    app = build_gateway(dense, lexical, store)
    return TestClient(app, base_url="http://127.0.0.1")


def test_search_lite(client):
    r = client.post("/search", json={"query": "cat", "type": "lite", "numResults": 10})
    assert r.status_code == 200
    assert "results" in r.json()


def test_search_auto(client):
    r = client.post("/search", json={"query": "cat", "type": "auto", "numResults": 10})
    assert r.status_code == 200
    assert "results" in r.json()


def test_unsupported_field_400(client):
    r = client.post("/search", json={"query": "cat", "type": "lite", "summary": True})
    assert r.status_code == 400


def test_index_version_mismatch_409(client):
    r = client.post(
        "/search",
        json={"query": "cat", "type": "lite"},
        headers={"X-Index-Version": "bogus"},
    )
    assert r.status_code == 409


def test_takedown_served(client):
    r = client.post(
        "/search",
        json={"query": "taken down secret content", "type": "lite", "numResults": 10},
    )
    ids = [x["id"] for x in r.json()["results"]]
    assert "https://x.com/c" not in ids


def test_contents_xor(client):
    r = client.post(
        "/contents", json={"urls": ["https://x.com/a", "https://x.com/missing"]}
    )
    assert r.status_code == 200
    results = r.json()["results"]
    statuses = {x["url"]: x["status"] for x in results}
    assert statuses["https://x.com/a"] == "ok"
    assert statuses["https://x.com/missing"] == "not_found"
    a = next(x for x in results if x["url"] == "https://x.com/a")
    assert a.get("text") or a.get("highlights")