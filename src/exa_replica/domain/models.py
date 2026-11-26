"""Internal domain models — pure, frozen (D85/D95).

`SearchResult` is deliberately NOT here: it is a Pydantic model at the inbound
boundary (D99/D102). These dataclasses are internal and never cross the wire
directly.
"""

from __future__ import annotations

from dataclasses import dataclass

from exa_replica.domain.errors import UnsupportedFilter


@dataclass(frozen=True, slots=True)
class Filters:
    """Query filters (D70). Applied before fusion; unsupported → UnsupportedFilter."""

    domains: tuple[str, ...] = ()
    start_date: str | None = None
    end_date: str | None = None
    category: str | None = None


def ensure_supported_filters(filters: Filters) -> None:
    """D70: apply fully or raise; date/category are unsupported in M1."""
    if filters.start_date or filters.end_date or filters.category:
        raise UnsupportedFilter(
            "date/category filters are unsupported in M1 (D70/D85)"
        )


@dataclass(frozen=True, slots=True)
class Passage:
    """A chunk of a document (D60). Offsets are UTF-8 bytes on NFC text (D78)."""

    passage_id: str
    doc_id: str
    text: str
    start: int
    end: int
    lang: str


@dataclass(frozen=True, slots=True)
class Hit:
    """A single retrieval hit; `passage_id` is the winning passage (D83)."""

    doc_id: str
    score: float
    passage_id: str


@dataclass(frozen=True, slots=True)
class Contents:
    """Internal content result for `/contents` (D20 status: ok|not_found|not_in_index)."""

    doc_id: str
    text: str
    highlights: tuple[str, ...]
    status: str