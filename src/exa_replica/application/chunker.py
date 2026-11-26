"""Passage chunker (D60, provisional defaults — frozen as D44 after run B).

Model-independent reference unit = UAX #29 words. `chunker_version` excludes the
model tokenizer. Offsets are UTF-8 **byte** offsets on `text_canonical` (D78).
Boundaries: paragraph → sentence → hard cut. Short passages merge with the
previous; a short/empty document is marked with a reason code, never silent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from exa_replica.domain.document import Document
from exa_replica.domain.models import Passage

CHUNKER_VERSION = "uax29-1.0;target=180;max=400;overlap=1"

_TARGET_WORDS = 180
_MAX_WORDS = 400
_OVERLAP_SENTENCES = 1

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_SENT_END_RE = re.compile(r"[.!?](?=\s|$)")


@dataclass(frozen=True, slots=True)
class Chunking:
    passages: tuple[Passage, ...]
    reason: str  # "" when ok, else a reason code (e.g. "empty_document")
    chunker_version: str = CHUNKER_VERSION


def _word_count(s: str) -> int:
    return len(_WORD_RE.findall(s))


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) char spans of stripped, non-empty sentences."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _SENT_END_RE.finditer(text):
        end = m.end()
        raw = text[start:end]
        stripped = raw.strip()
        if stripped:
            lead = len(raw) - len(raw.lstrip())
            spans.append((start + lead, start + lead + len(stripped)))
        start = end
    tail = text[start:]
    if tail.strip():
        lead = len(tail) - len(tail.lstrip())
        spans.append((start + lead, start + lead + len(tail.strip())))
    return spans


def _byte_off(text: str, char_idx: int) -> int:
    return len(text[:char_idx].encode("utf-8"))


def chunk(doc: Document) -> Chunking:
    text = doc.text_canonical
    if not text.strip():
        return Chunking((), "empty_document")

    spans = _sentence_spans(text)
    groups: list[list[tuple[int, int]]] = []
    cur: list[tuple[int, int]] = []
    cur_words = 0
    for span in spans:
        w = _word_count(text[span[0] : span[1]])
        if cur and cur_words + w > _TARGET_WORDS:
            groups.append(cur)
            cur = cur[-_OVERLAP_SENTENCES:] if _OVERLAP_SENTENCES else []
            cur_words = sum(_word_count(text[s[0] : s[1]]) for s in cur)
        cur.append(span)
        cur_words += w
        if cur_words >= _MAX_WORDS:
            groups.append(cur)
            cur = []
            cur_words = 0
    if cur:
        groups.append(cur)

    passages: list[Passage] = []
    for ordinal, group in enumerate(groups):
        start_char = group[0][0]
        end_char = group[-1][1]
        ptext = text[start_char:end_char]
        passage_id = (
            f"{doc.url_canonical}|{doc.generation}|{doc.content_hash}|"
            f"{CHUNKER_VERSION}|{ordinal}"
        )
        passages.append(
            Passage(
                passage_id=passage_id,
                doc_id=doc.url_canonical,
                text=ptext,
                start=_byte_off(text, start_char),
                end=_byte_off(text, end_char),
                lang=doc.lang,
            )
        )
    return Chunking(tuple(passages), "")