# RTX Pro 6000 runbook (owner-run)

The Thinkpad never builds (D39). The RTX Pro 6000 (96 GB, 128 GB RAM, 16 vCPU,
500 GB NVMe; D36) is the frozen measurement profile. The owner clones this repo
on the box and runs these steps; record each result against the profile in
`docs/hardware_reference.md` and amend the decision (value + source + date).

## 0. Setup (once)

```bash
git clone https://github.com/keypaa/exa-replica.git && cd exa-replica
uv python pin 3.12
uv sync
nvidia-smi   # confirm the RTX Pro 6000 is visible
```

## 1. Run B — passage spec (freezes D44)  [code ready: M1 extract/clean/chunk]

```bash
python bench/rtx/run_b_passage_spec.py --warc <path-or-url> --n 2000 --out bench/results/run_b.json
```
Measures tokens/word + overflow + passage stats on a T0 WARC sample; the output
run manifest freezes the `TBD-B` values in `docs/s4_passage_spec_skeleton.md` as
**D44** (amend the decision with the measured values + date).

## 2. D81 quality (nDCG@10 on dev)  [blocked: needs the judged golden set]

Needs the judged dev golden set (candidates retrieved from the T0 corpus). Build
the corpus first (step 3), then run the eval harness. **Blocked until the golden
set is judged.**

## 3. D82 R0/R1 + baseline build  [needs M3 build/index code]

The full build → index pipeline lands in M3. Once present:
```bash
python -m exa_replica.entrypoints.encode   # build embeddings/index (R0)
# then measure R0 p95/VRAM and R1 recall@100 vs R0 (D82)
```

## Notes

- Do **not** run build and serving simultaneously (mono-GPU, D68).
- Record VRAM idle/startup/peak, GPU-seconds, and the exact config per run.
- A10G (Modal) numbers are a lower bound; RTX Pro 6000 bf16 is the reference.