# RTX Pro 6000 runbook (blank box, owner-run)

The Thinkpad never builds (D39). The RTX Pro 6000 (96 GB, 128 GB RAM, 16 vCPU,
500 GB NVMe; D36) is the frozen measurement profile. Follow these steps on the
blank box; record each result against the profile in `docs/hardware_reference.md`
and amend the decision (value + source + date).

## 0. Install uv + clone (blank box)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# restart the shell or: source $HOME/.local/bin/env
git clone https://github.com/keypaa/exa-replica.git && cd exa-replica
uv python pin 3.12
uv sync
nvidia-smi    # confirm the RTX Pro 6000 is visible
```

## 1. Smoke-test the harness (no download, ~seconds)

```bash
uv run --with warcio python bench/rtx/run_b_passage_spec.py \
    --warc bench/fixtures/sample.warc --n 100 --out /tmp/run_b_smoke.json
cat /tmp/run_b_smoke.json
```
Expect `n_docs: 3`, `overflow_passages: 0`. This proves the pipeline runs.

## 2. Run B — passage spec (freezes D44)  [the key evidence]

Get a WARC (target crawl CC-MAIN-2026-43, D35):
```bash
WARC_URL="https://data.commoncrawl.org/$(bash bench/rtx/get_warc.sh)"
echo "$WARC_URL"
```
Then measure (use the model tokenizer for the real tokens/word, D60):
```bash
uv run --with warcio,transformers python bench/rtx/run_b_passage_spec.py \
    --warc "$WARC_URL" --n 2000 --out bench/results/run_b.json
cat bench/results/run_b.json
```
Record `tokens_per_word`, `passages_per_doc`, `overflow_passages` and freeze the
`TBD-B` values in `docs/s4_passage_spec_skeleton.md` as **D44** (amend the
decision with the measured values + date). Send `run_b.json` back.

## 3. D81 quality (nDCG@10 on dev)  [blocked: needs the judged golden set]

Needs the judged dev golden set (candidates retrieved from the T0 corpus). Build
the corpus first (step 4), then run the eval harness. **Blocked until the golden
set is judged.**

## 4. D82 R0/R1 + baseline build  [needs M3 build/index code]

The full build → index pipeline lands in M3. Once present:
```bash
python -m exa_replica.entrypoints.encode   # build embeddings/index (R0)
# then measure R0 p95/VRAM and R1 recall@100 vs R0 (D82)
```

## Notes

- Do **not** run build and serving simultaneously (mono-GPU, D68).
- Record VRAM idle/startup/peak, GPU-seconds, and the exact config per run.
- A10G (Modal) numbers are a lower bound; RTX Pro 6000 bf16 is the reference.
- `uv run --with <pkgs>` installs into an ephemeral overlay (not the lockfile).