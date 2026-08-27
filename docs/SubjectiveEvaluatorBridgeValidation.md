# Subjective Evaluator Bridge Validation

This standalone protocol compares the deprecated Princeton GEO judge with the pinned GPT-4o mini candidate. It does not update experiment rows, evaluator configuration, or the replication runner.

## Plan without API calls

From `backend/`:

```bash
venv/bin/python validate_subjective_evaluator_bridge.py
```

The default protocol samples 20 completed answers with random seed `20260820` and reports the number of paid calls required. A fixed seed makes the random sample reproducible.

## Execute

```bash
venv/bin/python validate_subjective_evaluator_bridge.py --execute
```

This authorizes 280 evaluator calls: 20 answers × 7 dimensions × 2 models. Results are checkpointed after every successful call under `verification_artifacts/subjective_evaluator_bridge/`. Re-running the same command resumes missing calls. Use `--restart` only when a new sample and a fresh validation are intended.

The generated report includes Pearson, Spearman, Kendall τ-b, MAE, per-dimension agreement, a Bland–Altman SVG, scatter SVGs, and discretized 1–5 confusion matrices in CSV and SVG formats.

The predeclared screening rule is intentionally explicit. Passing supports a disclosed contemporary evaluator migration, not a claim that GPT-4o mini is the historical Princeton measurement instrument.

