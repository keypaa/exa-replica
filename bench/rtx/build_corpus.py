"""Build the T0 corpus + indices (evidence/build harness, D35). Owner-run on RTX.

WARC -> extract -> clean -> chunk -> ContentStore (batched) + passages.jsonl +
dense vectors (.npy) + build manifest. Progress is printed to stderr. This is a
measurement/build harness, not the product serving path.

Run (RTX): uv run --with warcio,transformers,sentence-transformers,numpy \
    python bench/rtx/build_corpus.py --warc <path-or-url> --n 10000 \
    --out-dir bench/results/corpus --model intfloat/multilingual-e5-small
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

from exa_replica.adapters.outbound.clean import clean
from exa_replica.adapters.outbound.encoder import load_embedder
from exa_replica.adapters.outbound.extract import extract
from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.application.chunker import CHUNKER_VERSION, chunk


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _iter_html(path: str, n: int):
    from warcio.archiveiterator import ArchiveIterator

    stream = open(path, "rb") if not path.startswith("http") else urllib.request.urlopen(path)  # noqa: SIM115
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
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--out-dir", default="bench/results/corpus")
    ap.add_argument("--model", default="intfloat/multilingual-e5-small")
    ap.add_argument("--embed-batch", type=int, default=256)
    args = ap.parse_args()

    out = Path(args.out_dir)
    store = ContentStore(out / "store")

    _log(f"[1/3] reading WARC (n={args.n}) ...")
    items = []
    passages = []
    for i, (html, date) in enumerate(_iter_html(args.warc, args.n), 1):
        doc = clean(extract(html, date))
        if doc.exclusion == "none" and doc.text_canonical:
            ch = chunk(doc)
            if ch.passages:
                items.append((doc, ch.passages))
                passages.extend(ch.passages)
        if i % 500 == 0:
            _log(f"  extracted {i} records, {len(items)} docs, {len(passages)} passages")

    _log(f"[2/3] writing store ({len(items)} docs, {len(passages)} passages) ...")
    store.put_many(items)

    _log(f"[3/3] embedding {len(passages)} passages on GPU (model={args.model}) ...")
    embedder = load_embedder(args.model)
    vecs: list[list[float]] = []
    B = args.embed_batch
    for i in range(0, len(passages), B):
        vecs.extend(embedder.embed([p.text for p in passages[i : i + B]]))
        _log(f"  embedded {min(i + B, len(passages))}/{len(passages)}")
    vectors = np.asarray(vecs, dtype=np.float32) if vecs else np.zeros((0, 0), np.float32)
    np.save(out / "vectors.npy", vectors)
    with open(out / "passages.jsonl", "w") as f:
        f.writelines(json.dumps({"passage_id": p.passage_id, "doc_id": p.doc_id, "lang": p.lang, "start": p.start, "end": p.end}) + "\n" for p in passages)

    manifest = {
        "profile": "RTX Pro 6000",
        "model": args.model,
        "chunker_version": CHUNKER_VERSION,
        "n_docs": len(items),
        "n_passages": len(passages),
        "dim": int(vectors.shape[1]) if vectors.size else 0,
        "vectors_bytes": int(vectors.nbytes),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    _log(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()