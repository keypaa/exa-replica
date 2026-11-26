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


def _doc(url: str, text: str) -> Document:
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
    )


@pytest.fixture
def client(tmp_path):
    store = ContentStore(tmp_path)
    docs = [
        _doc("https://x.com/a", "the cat sat on the mat. It was warm today."),
        _doc("https://x.com/b", "dogs are loyal animals. They bark loudly."),
    ]
    passages = []
    for d in docs:
        ch = chunk(d)
        store.put(d, ch.passages)
        passages.extend(ch.passages)
    app = build_gateway(
        DenseIndex(Embedder(_FakeModel()), passages), BM25Index(passages), store
    )
    with TestClient(app, base_url="http://127.0.0.1") as c:
        yield c