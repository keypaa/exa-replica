from exa_replica.application.chunker import CHUNKER_VERSION, chunk
from exa_replica.domain.document import Document


def _doc(text: str, lang: str = "en") -> Document:
    return Document(
        url_canonical="https://x.com/a",
        generation="G",
        url_original="",
        warc_ref="",
        crawled_at="",
        title=None,
        published_date=None,
        author=None,
        lang=lang,
        text_canonical=text,
        content_hash="h",
        extractor_version="t",
    )


def test_offsets_utf8_on_accents():
    text = "Café naïve résumé. Voilà très bien. " * 40
    res = chunk(_doc(text))
    assert res.passages
    raw = text.encode("utf-8")
    for p in res.passages:
        # byte offsets must decode back to the passage text (D78)
        assert raw[p.start : p.end].decode("utf-8") == p.text


def test_no_empty_passage():
    res = chunk(_doc("One sentence. Two sentences. Three sentences."))
    assert all(p.text.strip() for p in res.passages)


def test_determinism_golden_hash():
    text = "Alpha beta gamma. Delta epsilon zeta. Eta theta iota. " * 30
    a = chunk(_doc(text))
    b = chunk(_doc(text))
    assert [p.passage_id for p in a.passages] == [p.passage_id for p in b.passages]
    assert a.chunker_version == b.chunker_version == CHUNKER_VERSION


def test_empty_doc_reason():
    res = chunk(_doc("   "))
    assert res.passages == ()
    assert res.reason == "empty_document"