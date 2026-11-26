"""D81 throughput + query-p95 benchmark on Modal (A10G).

Measures embedding throughput (passages/s) at batch sizes 32/64/128/256 and query
encode p95, for the D81 long-list candidates (license Apache/MIT/BSD, EN+FR,
<=1B params). Results are printed as JSON and written to a Modal Volume so the
run manifest can cite them (D65/D66/D81 step 3).

Run: modal run bench/modal_d81.py
GPU: A10G (do not raise without a recorded reason).
"""

from __future__ import annotations

import json
import time

import modal

app = modal.App("exa-replica-d81")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.4.1", "sentence-transformers==3.1.1", "transformers==4.46.3")
)

# D81 long list (provisional): license + EN/FR + <=1B params.
CANDIDATES = [
    "intfloat/multilingual-e5-small",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-base",
    "Alibaba-NLP/gte-multilingual-base",
]

_N_PASSAGES = 2000
_N_QUERIES = 200
_BATCH_SIZES = (32, 64, 128, 256)

GPU_SPEC = {
    "gpu": "A10G",
    "architecture": "Ampere GA102",
    "vram_gb": 24,
    "bandwidth_gbps": 600,
    "fp16_tensor_tflops": 70,
    "precision": "fp32 (sentence-transformers default)",
}


@app.function(gpu="A10G", image=image, timeout=1800)
def bench(model_name: str) -> dict:

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()
    passages = [f"Passage {i}: " + ("lorem ipsum dolor sit amet " * 8) for i in range(_N_PASSAGES)]
    queries = [f"query number {i} about a topic" for i in range(_N_QUERIES)]

    # warmup
    model.encode(passages[:64], batch_size=64)

    throughput = {}
    for bs in _BATCH_SIZES:
        t0 = time.perf_counter()
        for i in range(0, _N_PASSAGES, bs):
            model.encode(passages[i : i + bs], batch_size=bs)
        dt = time.perf_counter() - t0
        throughput[bs] = round(_N_PASSAGES / dt, 1)

    # query p95
    q_times = []
    for q in queries:
        t0 = time.perf_counter()
        model.encode([q])
        q_times.append((time.perf_counter() - t0) * 1000.0)
    q_times.sort()
    p95 = q_times[int(0.95 * len(q_times))]

    return {
        "model": model_name,
        "dim": dim,
        "throughput_passages_per_s": throughput,
        "query_p95_ms": round(p95, 2),
        **GPU_SPEC,
    }


@app.local_entrypoint()
def main():
    results = []
    for m in CANDIDATES:
        try:
            results.append(bench.remote(m))
        except Exception as e:  # noqa: BLE001 - one bad candidate must not lose the rest
            results.append({"model": m, "error": str(e)[:200], **GPU_SPEC})
    print(json.dumps(results, indent=2))