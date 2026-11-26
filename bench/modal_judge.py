"""LLM judge for the golden set (evidence, D35). Modal A10G.

Reads candidates.jsonl (from retrieve_candidates.py), labels each (query,
passage) 0-3 with a small instruct model on A10G, writes golden_dev.jsonl
(provisional; the human-calibrated judge + κ is the frozen path, §1.5/D14).

Run: modal run bench/modal_judge.py
"""

from __future__ import annotations

import json

import modal

app = modal.App("exa-replica-judge")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.4.1", "transformers==4.46.3", "accelerate==0.34.2")
    .env({"HF_HOME": "/cache"})
)

hf_cache = modal.Volume.from_name("exa-replica-hf", create_if_missing=True)

MODEL = "Qwen/Qwen2.5-7B-Instruct"

_PROMPT = (
    "You judge how relevant a web passage is to a search query and its objective.\n"
    "Query: {query}\nObjective: {objective}\nPassage:\n{passage}\n\n"
    "Rate relevance on a 0-3 scale: 0=irrelevant, 1=somewhat, 2=relevant, "
    "3=highly relevant. Reply with ONLY a JSON object: {{\"label\": N}}."
)


def _parse_label(text: str) -> int:
    import re

    m = re.search(r"\{[^}]*label[^}]*(\d)[^}]*\}", text)
    if m:
        return max(0, min(3, int(m.group(1))))
    m = re.search(r"\b([0-3])\b", text)
    return int(m.group(1)) if m else 0


@app.function(gpu="A10G", image=image, timeout=3600, volumes={"/cache": hf_cache})
def judge_batch(cands: list[dict]) -> list[dict]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.float16, device_map="auto"
    )
    out = []
    for c in cands:
        prompt = _PROMPT.format(
            query=c["query"], objective=c.get("objective", ""), passage=c["text"][:2000]
        )
        text = tok.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True
        )
        inputs = tok(text, return_tensors="pt").to(model.device)
        gen = model.generate(**inputs, max_new_tokens=24, do_sample=False)
        resp = tok.decode(gen[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)
        out.append({**c, "label": _parse_label(resp)})
    return out


@app.local_entrypoint()
def main():
    cands = [json.loads(l) for l in open("bench/results/candidates.jsonl") if l.strip()]
    results = judge_batch.remote(cands)
    with open("bench/results/golden_dev.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"judged {len(results)} candidates -> bench/results/golden_dev.jsonl")