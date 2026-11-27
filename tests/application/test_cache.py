from exa_replica.adapters.outbound.contents import ContentsProvider
from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.application.cache import (
    CacheLayer,
    contents_key,
    embedding_key,
)
from exa_replica.application.chunker import chunk
from exa_replica.domain.document import Document


def _doc(url: str, text: str) -> Document:
    return Document(
        url_canonical=url, generation="G", url_original=url, warc_ref="", crawled_at="",
        title=None, published_date=None, author=None, lang="en",
        text_canonical=text, content_hash="h", extractor_version="t",
    )


def test_embedding_cache_key():
    assert embedding_key("m", "p", "q") == ("m", "p", "q")
    assert embedding_key("m", "p", "q") != embedding_key("m", "p", "q2")


def test_contents_cache_key():
    assert contents_key("b", "u") == ("b", "u")
    assert contents_key("b", "u") != contents_key("b2", "u")


def test_degraded_not_cached():
    c = CacheLayer()
    c.put_contents("b", "u", "text", degraded=True)
    assert c.get_contents("b", "u") is None  # degraded never cached (D90)


def test_takedown_after_cache():
    c = CacheLayer()
    c.put_contents("b", "u", "text")
    assert c.get_contents("b", "u") == "text"
    # exclusions applied after cache read (D52)
    assert c.get_contents("b", "u", excluded=True) is None


def test_takedown_after_cache_provider(tmp_path):
    store = ContentStore(tmp_path)
    doc = _doc("https://x.com/a", "hello world text body")
    store.put(doc, chunk(doc).passages)
    cache = CacheLayer()
    assert ContentsProvider(store, cache, "b").fetch(["https://x.com/a"])[0]["status"] == "ok"
    p = ContentsProvider(store, cache, "b", is_excluded=lambda _u: True)
    assert p.fetch(["https://x.com/a"])[0]["status"] == "not_found"