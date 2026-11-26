"""Run B — passage-spec measurement (freezes D44). Owner-run on the RTX box.

Reads a T0 Common Crawl WARC sample, runs the M1 extract -> clean -> chunk
pipeline, and measures tokens/word + overflow + passage stats. The output run
manifest freezes the `TBD-B` values in `docs/s4_passage_spec_skeleton.md` as D44.

Run (RTX): uv run --with warcio python bench/rtx/run_b_passage_spec.py \
    --warc <path-or-url> --n 2000 --out bench/results/run_b.json

This script is a measurement harness (D35), not product code.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

from exa_replica.adapters.outbound.clean import clean
from exa_replica.adapters.outbound.extract import extract
from exa_replica.application.chunker import CHUNKER_VERSION, chunk


def _tokenizer():
    """Prefer the provisional model tokenizer; fall back to whitespace."""
    try:
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small")
        return lambda s: len(tok.encode(s))
    except Exception:  # noqa: BLE001 - tokenizer is optional; fall back to whitespace
        return lambda s: len(s.split())


def _iter_html(path: str, n: int):
    from warcio.archiveiterator import ArchiveIterator

    stream = open(path, "rb") if not path.startswith("http") else urllib.request.urlopen(path)  # noqa: SIM115 - consumed by ArchiveIterator
    count = 0
    for rec in ArchiveIterator(stream):
        if rec.rec_type != "response":
            continue
        yield rec.content_stream().read().decode("utf-8", "replace"), rec.rec_headers.get_header("WARC-Date", "")
        count += 1
        if count >= n:
            break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--warc", required=True)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--out", default="bench/results/run_b.json")
    args = ap.parse_args()

    ntok = _tokenizer()
    words = 0
    tokens = 0
    n_docs = 0
    n_passages = 0
    overflow = 0
    max_words = 400
    for html, warc_date in _iter_html(args.warc, args.n):
        doc = clean(extract(html, warc_date))
        if doc.exclusion == "too_short" or not doc.text_canonical:
            continue
        n_docs += 1
        words += len(doc.text_canonical.split())
        tokens += ntok(doc.text_canonical)
        ch = chunk(doc)
        n_passages += len(ch.passages)
        overflow += sum(1 for p in ch.passages if len(p.text.split()) > max_words)

    manifest = {
        "profile": "RTX Pro 6000",
        "chunker_version": CHUNKER_VERSION,
        "n_docs": n_docs,
        "n_passages": n_passages,
        "words": words,
        "tokens": tokens,
        "tokens_per_word": round(tokens / words, 4) if words else None,
        "passages_per_doc": round(n_passages / n_docs, 2) if n_docs else None,
        "overflow_passages": overflow,
        "max_words": max_words,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()