"""D82 index-settings benchmark on Modal A10G: R0 exact vs R1 binary+int8.

Loads the corpus vectors from the Volume, embeds the golden queries, and measures:
- R0 (exact bf16 matmul): top-k latency + recall (exact = 1.0 reference).
- R1 (binary Hamming scan + int8 rescore): recall@100 vs R0, K_bin sweep.

Run: modal run bench/modal_d82.py --k 100
"""

from __future__ import annotations

import json
import time

import modal

app = modal.App("exa-replica-d82")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch==2.4.1",
        "transformers==4.46.3",
        "sentence-transformers==3.1.1",
        "numpy",
    )
    .env({"HF_HOME": "/cache"})
    .add_local_dir("src/exa_replica", "/root/exa_replica")
    .add_local_file("docs/fixtures/exa-mcp/query_plan.jsonl", "/root/query_plan.jsonl")
)

cache = modal.Volume.from_name("exa-replica-hf", create_if_missing=True)
corpus = modal.Volume.from_name("exa-replica-corpus-vol", create_if_missing=True)


@app.function(gpu="A10G", image=image, volumes={"/cache": cache, "/corpus": corpus}, timeout=3600)
def bench(model: str, k: int) -> dict:
    import numpy as np
    import torch

    from exa_replica.adapters.outbound.encoder import load_embedder

    vecs = np.load("/corpus/vectors.npy").astype(np.float32)
    with open("/root/query_plan.jsonl") as f:
        queries = [json.loads(l) for l in f if l.strip()]
    embedder = load_embedder(model, device="cuda")
    Q = np.asarray(embedder.embed([q["query"] for q in queries]), dtype=np.float32)

    V = torch.from_numpy(vecs).to("cuda")
    Qv = torch.from_numpy(Q).to("cuda")

    # R0 exact
    t0 = time.perf_counter()
    scores = Qv @ V.T
    topk = scores.topk(k, dim=1).indices.cpu().numpy()
    r0_ms = (time.perf_counter() - t0) / len(queries) * 1000.0

    # R1 binary (sign) + int8 rescore
    B = torch.sign(V)
    Bq = torch.sign(Qv)
    results = {}
    for kbin in (500, 1000, 2000):
        t0 = time.perf_counter()
        hamming = (Bq @ B.T)  # higher = closer (same sign)
        cand = hamming.topk(min(kbin, V.shape[0]), dim=1).indices  # (nq, kbin)
        # int8 rescore the candidates (per query)
        recalls = []
        for qi in range(len(queries)):
            c = cand[qi]
            s = (Qv[qi] @ V[c].T)
            top = c[s.topk(k).indices]
            recalls.append(len(set(top.tolist()) & set(topk[qi].tolist())) / k)
        r1_ms = (time.perf_counter() - t0) / len(queries) * 1000.0
        results[kbin] = {"recall_at_k_vs_r0": round(sum(recalls) / len(recalls), 4), "ms_per_query": round(r1_ms, 3)}

    return {"profile": "Modal A10G", "model": model, "n_vectors": int(V.shape[0]), "k": k, "r0_exact_ms_per_query": round(r0_ms, 3), "r1": results}


@app.local_entrypoint()
def main(model: str = "intfloat/multilingual-e5-small", k: int = 100):
    print(json.dumps(bench.remote(model, k), indent=2))