"""Document domain model + canon-v1 URL canonicalization (D41/D43, §4.1.1).

`Document` is the minimal, immutable document record. `text_canonical` is the
reference for all byte offsets (D78). `canon_v1` is syntactic, conservative, and
shared by pipeline and API; it is frozen per generation (D43).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

# Closed tracking-parameter list (D43). Anything else in the query is kept.
_TRACKING_PARAMS = frozenset(
    {"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "_ga", "yclid"}
)
_TRACKING_PREFIXES = ("utm_",)


@dataclass(frozen=True, slots=True)
class Document:
    url_canonical: str
    generation: str
    url_original: str
    warc_ref: str
    crawled_at: str  # WARC-Date; never the publication date (D29)
    title: str | None
    published_date: str | None
    author: str | None
    lang: str  # "und" below the detector threshold (D76)
    text_canonical: str
    content_hash: str  # sha256(text_canonical) — exact dedup (D50)
    extractor_version: str
    canonical_hint: str | None = None  # rel=canonical, dedup only (D43)
    exclusion: str = "none"
    robots_directives: tuple[str, ...] = ()
    tdm_reserved: bool = False

    @property
    def doc_id(self) -> tuple[str, str]:
        """doc_id = (generation, url_canonical) (D18/D20/D29)."""
        return (self.generation, self.url_canonical)


def _remove_dot_segments(path: str) -> str:
    """RFC 3986 dot-segment removal that preserves a trailing slash (D43)."""
    trailing = path.endswith("/")
    out: list[str] = []
    for seg in path.split("/"):
        if seg == ".":
            continue
        if seg == "..":
            if out:
                out.pop()
            continue
        out.append(seg)
    res = "/".join(out)
    if not res.startswith("/"):
        res = "/" + res
    if trailing and not res.endswith("/"):
        res += "/"
    return res


def _is_tracking(key: str) -> bool:
    k = key.lower()
    return k in _TRACKING_PARAMS or any(k.startswith(p) for p in _TRACKING_PREFIXES)


def canon_v1(url: str) -> str:
    """Syntactic, conservative canonicalization (D43). No http/https or www merge."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if host:
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            pass
    try:
        port = parts.port
    except ValueError:
        port = None
    default = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    if port is not None and not default:
        host = f"{host}:{port}"
    path = quote(
        _remove_dot_segments(parts.path or ""),
        safe="/:@-._~!$&'()*+,;=%",
    )
    pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(k)
    ]
    query = urlencode(pairs, doseq=True)
    return urlunsplit((scheme, host, path, query, ""))


def host_matches(url: str, domains: Sequence[str]) -> bool:
    """D70 domain filter: exact host or whole-label subdomain; empty = match all."""
    if not domains:
        return True
    host = (urlsplit(url).hostname or "").lower()
    for d in domains:
        d = d.lower().lstrip(".")
        if host == d or host.endswith("." + d):
            return True
    return False