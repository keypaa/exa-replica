# κ-labeling kit (human judge calibration, §1.5/D14)

Gate 3 needs human relevance labels to calibrate the LLM judge (Cohen's κ ≥ 0.6).
This kit is the template; the owner labels 50–100 (query, doc) pairs **blind**
(no system/source shown).

## How to label
1. Take the dev golden candidates (`bench/results/golden_dev.jsonl` after a rebuild,
  or the fixture set).
2. For each row, read `query` + `objective` + `text` and assign a label:
   - **0** = irrelevant
   - **1** = somewhat relevant
   - **2** = relevant
   - **3** = highly relevant
3. Do **not** look at which system produced the doc (blind).
4. Save as `bench/results/human_labels.jsonl` with `{"query":..., "doc_id":..., "label":N}`.

## Compute κ
```python
from eval.judge import cohen_kappa
# preds = LLM labels, humans = your labels (aligned by row)
kappa = cohen_kappa(preds, humans)
print(kappa)  # need >= 0.6 (provisional)
```

## Notes
- 50–100 labels; 50–100 hand labels, blind, Cohen's κ (D14).
- Freeze the judge config + labels; recompute scores per version (D14).
- Send `human_labels.jsonl` + κ back; I'll freeze the judge + run Gate 3 (test split, once).