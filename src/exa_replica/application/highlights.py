"""Extractive highlights S0 (D84).

S0 returns the first sentences of the reference passage / stored text (default 1
excerpt / ≤3 sentences, D84 R3). No LLM. Works on stored text regardless of index
status, so `not_in_index` documents still get highlights. `guiding` (the query /
objective) is accepted for interface parity; S0 ignores it.
"""

from __future__ import annotations

import re

_MAX_SENTENCES = 3
_SENT_END_RE = re.compile(r"[.!?](?=\s|$)")


def _sentences(text: str) -> list[str]:
    out: list[str] = []
    start = 0
    for m in _SENT_END_RE.finditer(text):
        raw = text[start : m.end()].strip()
        if raw:
            out.append(raw)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def highlights(text: str, guiding: str = "") -> list[str]:
    if not text.strip():
        return []
    return _sentences(text)[:_MAX_SENTENCES]