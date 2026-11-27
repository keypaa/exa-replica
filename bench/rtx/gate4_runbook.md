# Gate 4 (blocking) runbook — RTX Pro 6000 (owner-run)

Gate 4 is the release-blocking performance gate (D15/D16), run on the **final
topology** with a **cold cache** (D90). The A10G did everything else; this is the
one run only the reference box can certify.

## 0. Setup
```bash
git clone https://github.com/keypaa/exa-replica.git && cd exa-replica
uv python pin 3.12 && uv sync
nvidia-smi    # RTX Pro 6000
```

## 1. Build the final index (if not already)
```bash
WARC_URL="https://data.commoncrawl.org/$(bash bench/rtx/get_warc.sh)"
uv run --with warcio,transformers,sentence-transformers,numpy \
    python bench/rtx/build_corpus.py --warc "$WARC_URL" --n 10000 \
    --out-dir bench/results/corpus --model intfloat/multilingual-e5-small
```

## 2. Start the final topology (cold cache)
```bash
# gateway + GPU worker + CPU worker (systemd units in deploy/, or run directly)
uv run python -m exa_replica.entrypoints.search &     # gateway (single-process fallback)
# or the systemd units: deploy/{gateway,worker-gpu,worker-cpu}.service
```
Cold cache: start fresh (no warm cache); declare cache state in the run (D16).

## 3. Run the D16 load test (k6, constant-arrival-rate)
- 10-min plateau + drain; isolated / mixed / saturation→recovery / cold.
- Per-route offered load; planned/sent/successful; frozen profile; time series.
- Record p50/p95/p99 latency, useful throughput, error budget, VRAM idle/startup/peak, GPU-seconds.

## 4. Pass criteria (D15/D16)
- `lite`: p50 ≤300 ms, p95 ≤600 ms, p99 ≤1 s, ≥50 req/s.
- `auto`: p50/p95/p99 per D15; useful throughput; error budget.
- Cold cache validated (D90); degraded declared; no partial success.

## 5. Record
Write the run manifest (config, time series, VRAM, GPU-seconds) to
`bench/results/gate4.json` and send it back. This + the κ-labeled Gate 3 are the
last two release blockers.