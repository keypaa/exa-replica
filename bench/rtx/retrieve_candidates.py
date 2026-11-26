"""Retrieve candidate passages for the golden queries (evidence, D35). RTX.

Loads the corpus built by build_corpus.py (store + passages.jsonl + vectors.npy),
runs dense + BM25 retrieval per golden query, fuses (RRF), and writes the top-K
candidates (with passage text) to candidates.jsonl for the LLM judge.

Run (RTX): uv run --with sentence-transformers,transformers,numpy \
    python bench/rtx/retrieve_candidates.py --corpus bench/results/corpus \
    --queries docs/fixtures/exa-mcp/query_plan.jsonl --k 20 \
    --out bench/results/candidates.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from exa_replica.adapters.outbound.bm25 import BM25Index
from exa_replica.adapters.outbound.encoder import load_embedder
from exa_replica.adapters.outbound.store import ContentStore
from exa_replica.application.fusion import fuse
from exa_replica.domain.models import Filters, Hit, Passage


def _load_passages(corpus: Path, store: ContentStore) -> list[Passage]:
    texts = store.all_texts()  # one read per shard, not per passage
    passages = []
    with open(corpus / "passages.jsonl") as f:
        for line in f:
            r = json.loads(line)
            text = texts.get(r["doc_id"], "")
            raw = text.encode("utf-8")
            ptext = raw[r["start"] : r["end"]].decode("utf-8", "replace")
            passages.append(
                Passage(r["passage_id"], r["doc_id"], ptext, r["start"], r["end"], r["lang"])
            )
    return passages


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="bench/results/corpus")
    ap.add_argument("--queries", default="docs/fixtures/exa-mcp/query_plan.jsonl")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--model", default="intfloat/multilingual-e5-small")
    ap.add_argument("--out", default="bench/results/candidates.jsonl")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    store = ContentStore(corpus / "store")
    passages = _load_passages(corpus, store)
    vectors = np.load(corpus / "vectors.npy")
    bm25 = BM25Index(passages)
    embedder = load_embedder(args.model, device="cuda")

    with open(args.queries) as qf:
        queries = [json.loads(l) for l in qf if l.strip()]
    print(f"loaded {len(passages)} passages, {len(queries)} queries; encoding on cuda", file=sys.stderr, flush=True)
    with open(args.out, "w") as out:
        for qi, q in enumerate(queries, 1):
            if qi % 5 == 0:
                print(f"  query {qi}/{len(queries)}", file=sys.stderr, flush=True)
            qvec = np.asarray(embedder.embed([q["query"]])[0], dtype=np.float32)
            scores = vectors @ qvec
            order = np.argsort(-scores)[: args.k]
            dense_hits = [
                Hit(passages[i].doc_id, float(scores[i]), passages[i].passage_id)
                for i in order
            ]
            bm25_hits = bm25.search(q["query"], Filters(), args.k, 1e9)
            fused = fuse(bm25_hits, dense_hits)[: args.k]
            by_id = {p.passage_id: p for p in passages}
            for dh in fused:
                p = by_id.get(dh.passage_id)
                out.write(
                    json.dumps(
                        {
                            "query": q["query"],
                            "objective": q.get("objective", ""),
                            "doc_id": dh.doc_id,
                            "passage_id": dh.passage_id,
                            "text": p.text if p else "",
                        }
                    )
                    + "\n"
                )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()