"""Full evidence pipeline on Modal A10G: build corpus -> retrieve -> LLM judge.

Frees the RTX box: the corpus lives in a Modal Volume; build/retrieve/judge run
on A10G. Outputs (manifest, candidates, golden) are returned and written locally.

Run: modal run bench/modal_pipeline.py --n 10000
Smoke: modal run bench/modal_pipeline.py --n 200
"""

from __future__ import annotations

import json

import modal

app = modal.App("exa-replica-pipeline")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch==2.4.1",
        "transformers==4.46.3",
        "sentence-transformers==3.1.1",
        "accelerate==0.34.2",
        "warcio",
        "trafilatura",
        "numpy",
        "pyarrow",
    )
    .env({"PYTHONPATH": "/root", "HF_HOME": "/cache"})
    # add_local_* must be last (Modal adds them at container startup).
    .add_local_dir("src/exa_replica", "/root/exa_replica")
    .add_local_file("docs/fixtures/exa-mcp/query_plan.jsonl", "/root/query_plan.jsonl")
)

hf_cache = modal.Volume.from_name("exa-replica-hf", create_if_missing=True)
corpus_vol = modal.Volume.from_name("exa-replica-corpus-vol", create_if_missing=True)

GEN = "CC-MAIN-2026-43"
JUDGE_MODEL = "Qwen/Qwen2.5-7B-Instruct"


@app.function(
    gpu="A10G",
    image=image,
    volumes={"/cache": hf_cache, "/corpus": corpus_vol},
    timeout=7200,
)
def run(warc_url: str, n: int, model: str, k: int = 20) -> dict:
    import urllib.request
    from dataclasses import replace

    import numpy as np
    from warcio.archiveiterator import ArchiveIterator

    from exa_replica.adapters.outbound.bm25 import BM25Index
    from exa_replica.adapters.outbound.clean import clean
    from exa_replica.adapters.outbound.encoder import load_embedder
    from exa_replica.adapters.outbound.extract import extract
    from exa_replica.adapters.outbound.store import ContentStore
    from exa_replica.application.chunker import CHUNKER_VERSION, chunk
    from exa_replica.application.fusion import fuse
    from exa_replica.domain.document import canon_v1
    from exa_replica.domain.models import Filters, Hit, Passage

    # ---- build ----
    store = ContentStore("/corpus/store")
    items, passages = [], []
    stream = urllib.request.urlopen(warc_url)
    count = 0
    for rec in ArchiveIterator(stream):
        if rec.rec_type != "response":
            continue
        url = rec.rec_headers.get_header("WARC-Target-URI", "")
        html = rec.content_stream().read().decode("utf-8", "replace")
        date = rec.rec_headers.get_header("WARC-Date", "")
        doc = replace(
            clean(extract(html, date)),
            url_canonical=canon_v1(url),
            url_original=url,
            generation=GEN,
        )
        if doc.exclusion == "none" and doc.text_canonical:
            ch = chunk(doc)
            if ch.passages:
                items.append((doc, ch.passages))
                passages.extend(ch.passages)
        count += 1
        if count >= n:
            break
    store.put_many(items)
    embedder = load_embedder(model, device="cuda")
    vecs = []
    for i in range(0, len(passages), 256):
        vecs.extend(embedder.embed([p.text for p in passages[i : i + 256]]))
    vectors = np.asarray(vecs, dtype=np.float32) if vecs else np.zeros((0, 0), np.float32)
    np.save("/corpus/vectors.npy", vectors)
    with open("/corpus/passages.jsonl", "w") as f:
        f.writelines(json.dumps({"passage_id": p.passage_id, "doc_id": p.doc_id, "lang": p.lang, "start": p.start, "end": p.end}) + "\n" for p in passages)
    manifest = {
        "profile": "Modal A10G",
        "model": model,
        "chunker_version": CHUNKER_VERSION,
        "generation": GEN,
        "n_docs": len(items),
        "n_passages": len(passages),
        "empty_url_docs": sum(1 for d, _ in items if not d.url_canonical),
        "dim": int(vectors.shape[1]) if vectors.size else 0,
    }

    # ---- retrieve ----
    texts = store.all_texts()
    passages2 = []
    with open("/corpus/passages.jsonl") as f:
        for line in f:
            r = json.loads(line)
            t = texts.get(r["doc_id"], "")
            raw = t.encode("utf-8")
            passages2.append(Passage(r["passage_id"], r["doc_id"], raw[r["start"]:r["end"]].decode("utf-8", "replace"), r["start"], r["end"], r["lang"]))
    bm25 = BM25Index(passages2)
    by_id = {p.passage_id: p for p in passages2}
    with open("/root/query_plan.jsonl") as f:
        queries = [json.loads(l) for l in f if l.strip()]
    candidates = []
    for q in queries:
        qvec = np.asarray(embedder.embed([q["query"]])[0], dtype=np.float32)
        scores = vectors @ qvec
        order = np.argsort(-scores)[:k]
        dense_hits = [Hit(passages2[i].doc_id, float(scores[i]), passages2[i].passage_id) for i in order]
        fused = fuse(bm25.search(q["query"], Filters(), k, 1e9), dense_hits)[:k]
        for dh in fused:
            p = by_id.get(dh.passage_id)
            candidates.append({"query": q["query"], "objective": q.get("objective", ""), "doc_id": dh.doc_id, "passage_id": dh.passage_id, "text": p.text if p else ""})

    # ---- judge ----
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(JUDGE_MODEL)
    jmodel = AutoModelForCausalLM.from_pretrained(JUDGE_MODEL, torch_dtype=torch.float16, device_map="auto")
    import re

    def parse_label(t):
        m = re.search(r"\{[^}]*label[^}]*(\d)[^}]*\}", t)
        if m:
            return max(0, min(3, int(m.group(1))))
        m = re.search(r"\b([0-3])\b", t)
        return int(m.group(1)) if m else 0

    golden = []
    for c in candidates:
        prompt = (
            f"Rate relevance 0-3 (0=irrelevant,3=highly relevant) of the passage to the query/objective.\n"
            f"Query: {c['query']}\nObjective: {c['objective']}\nPassage:\n{c['text'][:2000]}\n"
            'Reply ONLY JSON: {"label": N}.'
        )
        text = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt").to(jmodel.device)
        gen = jmodel.generate(**inputs, max_new_tokens=24, do_sample=False)
        resp = tok.decode(gen[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        golden.append({**c, "label": parse_label(resp)})

    return {"manifest": manifest, "candidates": candidates, "golden": golden}


@app.local_entrypoint()
def main(n: int = 10000, model: str = "intfloat/multilingual-e5-small", k: int = 20):
    import os

    warc_url = os.environ.get("WARC_URL", "")
    if not warc_url:
        raise SystemExit("set WARC_URL (a CC WARC path/URL)")
    out = run.remote(warc_url, n, model, k)
    os.makedirs("bench/results", exist_ok=True)
    with open("bench/results/candidates.jsonl", "w") as f:
        f.writelines(json.dumps(c) + "\n" for c in out["candidates"])
    with open("bench/results/golden_dev.jsonl", "w") as f:
        f.writelines(json.dumps(g) + "\n" for g in out["golden"])
    with open("bench/results/corpus_manifest.json", "w") as f:
        json.dump(out["manifest"], f, indent=2)
    print(json.dumps(out["manifest"], indent=2))
    print(f"candidates={len(out['candidates'])} golden={len(out['golden'])}")