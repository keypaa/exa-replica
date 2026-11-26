"""Lexical index (D83) — provisional pure-Python BM25.

Tantivy is the frozen v1 target (D83); `tantivy-py` has no cp312 wheel, so M1
uses this provisional BM25 behind the `LexicalIndex` port (swap on the reference
box). Two fields `text_en`/`text_fr`; a passage is indexed in its language field;
queries hit both fields. k1=1.2, b=0.75 fixed (D83). Document score = max over
passages is applied later (fusion, Task 7). Domain filters (D70) are applied
before scoring; unsupported filters raise `UnsupportedFilter`.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

from exa_replica.domain.document import host_matches
from exa_replica.domain.models import Filters, Hit, Passage, ensure_supported_filters

_K1 = 1.2
_B = 0.75
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return _TOKEN_RE.findall(folded)


class BM25Index:
    K1 = _K1
    B = _B

    def __init__(self, passages: Sequence[Passage]) -> None:
        self._version = "bm25-py-provisional-1"
        self._field_docs: dict[str, list[Counter[str]]] = {"text_en": [], "text_fr": []}
        self._field_len: dict[str, list[int]] = {"text_en": [], "text_fr": []}
        self._field_passage: dict[str, list[Passage]] = {"text_en": [], "text_fr": []}
        self._df: dict[str, Counter[str]] = {"text_en": Counter(), "text_fr": Counter()}
        self._by_id: dict[str, Passage] = {}
        for p in passages:
            field = "text_fr" if p.lang == "fr" else "text_en"
            tokens = _tokenize(p.text)
            counts = Counter(tokens)
            self._field_docs[field].append(counts)
            self._field_len[field].append(len(tokens))
            self._field_passage[field].append(p)
            self._by_id[p.passage_id] = p
            for term in counts:
                self._df[field][term] += 1
        self._avglen = {
            f: (sum(self._field_len[f]) / len(self._field_len[f]))
            if self._field_len[f]
            else 0.0
            for f in ("text_en", "text_fr")
        }

    def _score_field(self, query_terms: list[str], field: str) -> list[float]:
        docs = self._field_docs[field]
        lengths = self._field_len[field]
        avg = self._avglen[field] or 1.0
        n = len(docs)
        scores = [0.0] * n
        for term in query_terms:
            df = self._df[field].get(term, 0)
            if df == 0:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i, counts in enumerate(docs):
                tf = counts.get(term, 0)
                if tf == 0:
                    continue
                denom = tf + _K1 * (1 - _B + _B * lengths[i] / avg)
                scores[i] += idf * (tf * (_K1 + 1)) / denom
        return scores

    def search(
        self, query: str, filters: Filters, k: int, deadline: float
    ) -> list[Hit]:
        ensure_supported_filters(filters)
        terms = _tokenize(query)
        if not terms or deadline <= 0:
            return []
        # Score per passage (each passage lives in exactly one field); apply the
        # domain filter (D70) before ranking.
        per_passage: dict[str, float] = {}
        for field in ("text_en", "text_fr"):
            for i, s in enumerate(self._score_field(terms, field)):
                if s <= 0:
                    continue
                p = self._field_passage[field][i]
                if not host_matches(p.doc_id, filters.domains):
                    continue
                per_passage[p.passage_id] = per_passage.get(p.passage_id, 0.0) + s
        ranked = sorted(per_passage.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        return [
            Hit(self._by_id[pid].doc_id, score, pid) for pid, score in ranked
        ]

    def stats(self) -> dict[str, float | int | str]:
        return {
            "text_en": len(self._field_docs["text_en"]),
            "text_fr": len(self._field_docs["text_fr"]),
            "k1": _K1,
            "b": _B,
        }

    def version(self) -> str:
        return self._version