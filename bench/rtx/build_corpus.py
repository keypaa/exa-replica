"""Build the T0 corpus + indices (evidence/build harness, D35). Owner-run on RTX.

WARC -> extract -> clean -> chunk -> ContentStore + passages.jsonl + dense
vectors (.npy) + build manifest. Outputs feed the golden-set build, D81 quality,
and D82. This is a measurement/build harness, not the product serving path.

Run (RTX): uv run --with warcio,transformers,sentence-transformers,numpy \
    python bench/rtx/build_corpus.py --warc <path-or-url> --n 10000 \
    --out-dir bench/results/corpus --model intfloat/multilingual-e5-small
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

import numpy as np

from exa_replica.adapters.outbound.clean import clean
from exa_replica.adapters.outbound.encoder import load_embedder
from exa_replica.adapters.outbound.extract import extract
from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.application.chunker import CHUNKER_VERSION, chunk


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
    args = ap.parse_args()

    out = Path(args.out_dir)
    store = ContentStore(out / "store")
    passages = []
    n_docs = 0
    for html, date in _iter_html(args.warc, args.n):
        doc = clean(extract(html, date))
        if doc.exclusion != "none" or not doc.text_canonical:
            continue
        ch = chunk(doc)
        if not ch.passages:
            continue
        store.put(doc, ch.passages)
        passages.extend(ch.passages)
        n_docs += 1

    embedder = load_embedder(args.model)
    vectors = np.asarray(embedder.embed([p.text for p in passages]), dtype=np.float32) if passages else np.zeros((0, 0), np.float32)
    np.save(out / "vectors.npy", vectors)
    with open(out / "passages.jsonl", "w") as f:
        f.writelines(json.dumps({"passage_id": p.passage_id, "doc_id": p.doc_id, "lang": p.lang, "start": p.start, "end": p.end}) + "\n" for p in passages)

    manifest = {
        "profile": "RTX Pro 6000",
        "model": args.model,
        "chunker_version": CHUNKER_VERSION,
        "n_docs": n_docs,
        "n_passages": len(passages),
        "dim": int(vectors.shape[1]) if vectors.size else 0,
        "vectors_bytes": int(vectors.nbytes),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()