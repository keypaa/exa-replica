from fastapi.testclient import TestClient

from exa_replica.adapters.outbound.ann import DenseIndex
from exa_replica.adapters.outbound.bm25 import BM25Index
from exa_replica.adapters.outbound.encoder import Embedder
from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.application.chunker import chunk
from exa_replica.application.fusion import fuse
from exa_replica.bootstrap.composition import build_gateway
from exa_replica.domain.document import Document, canon_v1
from exa_replica.domain.models import Filters, Hit, Passage


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


def _client(tmp_path, docs):
    store = ContentStore(tmp_path)
    passages = []
    for d in docs:
        ch = chunk(d)
        store.put(d, ch.passages)
        passages.extend(ch.passages)
    app = build_gateway(
        DenseIndex(Embedder(_FakeModel()), passages), BM25Index(passages), store
    )
    return TestClient(app, base_url="http://127.0.0.1")


def test_search_returns_results(tmp_path):
    c = _client(tmp_path, [_doc("https://x.com/a", "the cat sat on the mat. It was warm today.")])
    r = c.post("/search", json={"query": "cat", "type": "lite", "numResults": 10})
    assert r.json()["results"]  # non-empty: the core deliverable


def test_domain_filter(tmp_path):
    docs = [
        _doc("https://a.com/x", "cat content here today."),
        _doc("https://b.com/y", "cat content here too today."),
    ]
    c = _client(tmp_path, docs)
    r = c.post(
        "/search",
        json={"query": "cat", "type": "lite", "numResults": 10, "includeDomains": ["a.com"]},
    )
    ids = [x["id"] for x in r.json()["results"]]
    assert ids and all("a.com" in i for i in ids)


def test_takedown(tmp_path):
    c = _client(tmp_path, [_doc("https://x.com/c", "taken down secret content.", exclusion="takedown")])
    assert c.post("/search", json={"query": "taken down secret", "type": "lite"}).json()["results"] == []
    r = c.post("/contents", json={"urls": ["https://x.com/c"]}).json()
    assert r["results"][0]["status"] == "not_found"


def test_canon_percent_idempotent():
    once = canon_v1("https://x.com/A%20B")
    assert canon_v1(once) == once  # no double-encoding (D43)


def test_fusion_keeps_best_rank():
    fused = fuse([Hit("d1", 9, "p_best"), Hit("d1", 8, "p_worse"), Hit("d2", 7, "p2")], [])
    d1 = next(h for h in fused if h.doc_id == "d1")
    assert d1.passage_id == "p_best"


def test_bm25_mixed_lang():
    ps = [
        Passage("p_fr", "https://fr.com/a", "le chat", 0, 7, "fr"),
        Passage("p_en", "https://en.com/b", "the cat", 0, 7, "en"),
    ]
    hits = BM25Index(ps).search("cat", Filters(), 10, 1e9)
    assert hits[0].doc_id == "https://en.com/b"
    assert hits[0].passage_id == "p_en"