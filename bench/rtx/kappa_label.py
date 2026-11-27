"""κ-labeling helper (Gate 3, §1.5/D14).

prepare: write a BLIND template (query, objective, text, llm_label, human_label=null)
for N rows of the dev golden set. You fill human_label (0-3) by reading, ignoring
llm_label. score: Cohen's κ of the LLM labels vs your labels (need >= 0.6).

Run:
  uv run python bench/rtx/kappa_label.py prepare --n 100
  # edit bench/results/human_labels.jsonl -> set human_label (0-3) on each row
  uv run python bench/rtx/kappa_label.py score
"""

from __future__ import annotations

import argparse
import json

from eval.judge import cohen_kappa


def prepare(src: str, out: str, n: int) -> None:
    rows = [json.loads(line) for line in open(src) if line.strip()][:n]
    with open(out, "w") as f:
        for r in rows:
            f.write(
                json.dumps(
                    {
                        "query": r["query"],
                        "objective": r.get("objective", ""),
                        "doc_id": r["doc_id"],
                        "text": r["text"][:1500],
                        "llm_label": r["label"],
                        "human_label": None,
                    }
                )
                + "\n"
            )
    print(f"wrote {len(rows)} rows to {out} — fill human_label (0-3), BLIND")


def score(path: str) -> None:
    rows = [json.loads(line) for line in open(path) if line.strip()]
    pairs = [
        (r["llm_label"], r["human_label"])
        for r in rows
        if r.get("human_label") is not None
    ]
    if not pairs:
        print("no human_label filled yet")
        return
    preds = [p for p, _ in pairs]
    humans = [h for _, h in pairs]
    print(f"n={len(pairs)}  kappa={cohen_kappa(preds, humans):.3f}  (need >= 0.6)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "score"])
    ap.add_argument("--src", default="bench/results/golden_dev.jsonl")
    ap.add_argument("--out", default="bench/results/human_labels.jsonl")
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()
    if args.cmd == "prepare":
        prepare(args.src, args.out, args.n)
    else:
        score(args.out)