"""Cleaning (D77): NFC → control chars → whitespace → min length → exact dedup.

Near-dedup (MinHash) is later. A short document is not dropped silently: it is
marked with a reason code (§4.1.2). Returns a new frozen `Document` with the
recomputed `content_hash`.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import replace

from exa_replica.domain.document import Document

_MIN_LEN = 10  # provisional; D77 threshold TBD
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACES_RE = re.compile(r"[ \t]+")
_BLANKS_RE = re.compile(r"\n{3,}")


def clean(doc: Document) -> Document:
    text = unicodedata.normalize("NFC", doc.text_canonical)
    text = _CTRL_RE.sub("", text)
    text = _SPACES_RE.sub(" ", text)
    text = _BLANKS_RE.sub("\n\n", text).strip()
    exclusion = doc.exclusion
    if len(text) < _MIN_LEN and exclusion == "none":
        exclusion = "too_short"
    return replace(
        doc,
        text_canonical=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        exclusion=exclusion,
    )