from exa_replica.adapters.outbound.clean import clean
from exa_replica.domain.document import Document


def _doc(text: str) -> Document:
    return Document(
        url_canonical="https://x.com/a",
        generation="CC-MAIN-2026-43",
        url_original="https://x.com/a",
        warc_ref="f,0,1",
        crawled_at="2026-11-20T00:00:00Z",
        title="t",
        published_date=None,
        author=None,
        lang="en",
        text_canonical=text,
        content_hash="",
        extractor_version="test",
    )


def test_nfc_normalization():
    # e + combining acute → composed é (NFC)
    cleaned = clean(_doc("cafe\u0301"))
    assert cleaned.text_canonical == "café"


def test_control_chars_removed():
    assert clean(_doc("a\x00b\x07c")).text_canonical == "abc"


def test_short_doc_excluded_with_reason():
    cleaned = clean(_doc("hi"))
    assert cleaned.exclusion == "too_short"


def test_content_hash_recomputed():
    cleaned = clean(_doc("hello world"))
    assert len(cleaned.content_hash) == 64
    assert cleaned.content_hash != ""