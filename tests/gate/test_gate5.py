"""Gate 5 (D17): determinism / idempotence / provenance (A10G-doable parts)."""

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


def test_gate5_ops():
    doc = _doc("https://x.com/a", "Hello world. This is a deterministic document body.")
    a = chunk(doc)
    b = chunk(doc)
    # byte-exact / idempotent (D17 5b): same input -> same passages
    assert [p.passage_id for p in a.passages] == [p.passage_id for p in b.passages]
    assert a.chunker_version == b.chunker_version
    # provenance: chunker_version is recorded (D17 5c)
    assert a.chunker_version