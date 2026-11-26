from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.application.chunker import chunk
from exa_replica.domain.document import Document


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


def test_roundtrip_text(tmp_path):
    store = ContentStore(tmp_path)
    doc = _doc("https://x.com/a", "Hello world. This is text.")
    store.put(doc, chunk(doc).passages)
    assert store.get_text("https://x.com/a") == "Hello world. This is text."


def test_passage_offsets_only(tmp_path):
    store = ContentStore(tmp_path)
    doc = _doc("https://x.com/a", "Hello world. This is text.")
    store.put(doc, chunk(doc).passages)
    text = store.get_text("https://x.com/a")
    raw = text.encode("utf-8")
    for p, ptext in store.get_passages("https://x.com/a"):
        # passage text is reconstructed from doc text + offsets (not stored)
        assert raw[p.start : p.end].decode("utf-8") == ptext
        assert p.text == ""


def test_shard_by_hash(tmp_path):
    store = ContentStore(tmp_path, n_shards=4)
    s1 = store.shard_of("https://x.com/a")
    assert s1 == store.shard_of("https://x.com/a")
    assert 0 <= s1 < 4


def test_put_many_roundtrip(tmp_path):
    store = ContentStore(tmp_path)
    docs = [_doc("https://x.com/a", "alpha text"), _doc("https://x.com/b", "beta text")]
    store.put_many([(d, chunk(d).passages) for d in docs])
    assert store.get_text("https://x.com/a") == "alpha text"
    assert store.get_text("https://x.com/b") == "beta text"