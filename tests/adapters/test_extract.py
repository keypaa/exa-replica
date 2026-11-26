from exa_replica.adapters.outbound.extract import extract

HTML = (
    "<html lang='en'><head><meta charset='utf-8'>"
    "<meta property='article:published_time' content='2024-01-02T03:04:05Z'>"
    "<title>T</title></head>"
    "<body><p>Hello world. This is a sufficiently long test document body "
    "with several sentences so the extractor returns real text.</p></body></html>"
)


def test_extract_fills_lang_and_date():
    doc = extract(HTML, warc_date="2026-11-20T00:00:00Z")
    assert doc.crawled_at == "2026-11-20T00:00:00Z"
    # published_date comes from the meta, never from warc_date (D29/§4.1.1)
    assert doc.published_date == "2024-01-02T03:04:05Z"
    assert doc.lang == "en"
    assert doc.text_canonical
    assert len(doc.content_hash) == 64


def test_extract_falls_back_to_und_when_no_lang():
    doc = extract("<html><body><p>Some text that is long enough to extract.</p></body></html>", "2026-11-20T00:00:00Z")
    assert doc.lang == "und"
    assert doc.published_date is None