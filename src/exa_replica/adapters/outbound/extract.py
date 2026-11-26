"""HTML extractor (D42): trafilatura default, resiliparse fallback.

`extract` is URL-agnostic: it fills `crawled_at` from the WARC date and
`published_date` from the document metadata (never the WARC date, D29). The
pipeline fills the URL fields afterwards.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

import trafilatura

from exa_replica.domain.document import Document

_META_DATE_RE = re.compile(
    r"<meta[^>]+(?:property|name)=[\"']"
    r"(?:article:published_time|datePublished|publishdate|pubdate)"
    r"[\"'][^>]+content=[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_HTML_LANG_RE = re.compile(r"<html[^>]+\blang=[\"']([^\"']+)[\"']", re.IGNORECASE)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _extract_text(html: str) -> str:
    text = trafilatura.extract(
        html, include_comments=False, include_tables=False, favor_recall=True
    )
    if not text:
        # resiliparse fallback (D42) if available.
        try:
            from resiliparse.extract.html import extract_text as _rs

            text = _rs(html)
        except Exception:  # noqa: BLE001 - fallback must never crash extraction
            text = ""
    return _nfc((text or "").strip())


def extract(html: str, warc_date: str) -> Document:
    text = _extract_text(html)
    lang_m = _HTML_LANG_RE.search(html)
    lang = lang_m.group(1).lower() if lang_m else "und"
    date_m = _META_DATE_RE.search(html)
    published = date_m.group(1) if date_m else None
    title_m = _TITLE_RE.search(html)
    title = _nfc(title_m.group(1).strip()) if title_m else None
    return Document(
        url_canonical="",  # filled by the pipeline (extract is URL-agnostic)
        generation="",
        url_original="",
        warc_ref="",
        crawled_at=warc_date,
        title=title,
        published_date=published,
        author=None,
        lang=lang,
        text_canonical=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        extractor_version=f"trafilatura-{trafilatura.__version__}",
    )