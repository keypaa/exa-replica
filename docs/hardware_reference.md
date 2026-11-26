# Hardware reference (measurement profiles)

Evidence is measured on a pinned profile and recorded with the run manifest so
results are comparable later (D36/D39). Two profiles exist:

## A10G (Modal) — current evidence card

Source: NVIDIA A10/A10G datasheet + AWS A10G datasheet (consulted 2026-11-26).

| Spec | A10G |
|---|---|
| Architecture | Ampere (GA102), 9,216 CUDA cores, 3rd-gen Tensor Cores |
| GPU memory | 24 GB GDDR6 (ECC) |
| Memory bandwidth | 600 GB/s |
| FP32 | 35 TFLOPS |
| TF32 Tensor | 35 TF (70 sparse) |
| BF16 / FP16 Tensor | 70 TF (140 sparse) |
| INT8 Tensor | 140 TOPS (280 sparse) |
| Interconnect | PCIe Gen4, 64 GB/s |
| Form factor / TDP | 2-slot FHFL, 300 W (AWS variant) |

Note: the A10 (150 W, single-slot) shares VRAM/bandwidth; A10G is the AWS variant.
Fits ~12B params at FP16. Used for **small/medium** evidence work only (D39).

## RTX Pro 6000 (reference box) — target profile (D36)

96 GB VRAM, 128 GB RAM, 16 vCPU, 500 GB NVMe. The frozen v1 measurement profile;
heavy work (run B/T0 ingest, D81 quality, D82, baseline build) runs here. The
Thinkpad never builds (D39). RTX results are produced by the owner from the
scripts in `bench/` and recorded against this profile.

## Benchmark config → result convention

Each benchmark records: profile (A10G / RTX Pro 6000), model id + revision,
precision (fp32/bf16/fp16), batch size, and the metric. A10G numbers are a
lower bound; the same config on the RTX Pro 6000 is the frozen reference.