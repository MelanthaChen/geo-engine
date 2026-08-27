# Princeton GEO Staged Validation Protocol

Date: 2026-08-20

This protocol validates methodological fidelity and qualitative trend reproduction. It does not treat equality with historical GPT-3.5 numbers as the success criterion.

## Paper conclusions under test

The machine-readable source of truth is `backend/app/experiment/paper_conclusions.json`. It separates conclusions testable by the main public experiment from conclusions that require rank analysis, tag analysis, pairwise strategy execution, or the historical Perplexity protocol.

Main-experiment checks include:

- Quotation Addition, Statistics Addition and Cite Sources each outperform baseline on PAWC.
- The full PAWC ordering has at least 80% pairwise concordance with Table 1.
- Fluency Optimization and Easy-to-Understand improve PAWC.
- Authoritative has limited PAWC gain.
- Keyword Stuffing has little or no PAWC gain.
- Quotation Addition, Statistics Addition and Cite Sources improve calibrated Subjective Impression.

The paper itself has a minor narrative/table tension: Section 4 groups Cite Sources among the three “top-performing” methods, while rounded Table 1 PAWC places Fluency at 24.7 and Cite Sources at 24.6. The protocol does not reinterpret that prose as a strict numerical top-three assertion. It tests the headline trio against baseline and independently measures concordance with the complete Table 1 ordering.

## Nested deterministic stages

All stages load the 997 valid official test rows, shuffle once with seed 42, then take a prefix. Therefore each later stage contains every query from the earlier stage.

| Stage | Queries | Proceed threshold |
|---|---:|---:|
| Stage 1 | 30 | 80% trend similarity |
| Stage 2 | 100 | 85% trend similarity |
| Stage 3 | 300 | 90% trend similarity |
| Full | 997 | 90% trend similarity |

A stage stops when it is incomplete, lacks testable evidence, or falls below its threshold. A failed gate must be investigated before the next budget is authorized. Unsupported secondary-paper claims remain `NOT_TESTED`; they are not counted as failures or silently counted as passes.

## Cost planning and execution gates

Planning never calls a provider:

```bash
cd backend
venv/bin/python run_official_geo_replication.py --plan --subjective
```

Execution requires an exact confirmation token:

```bash
venv/bin/python run_official_geo_replication.py \
  --stage stage1 \
  --subjective \
  --confirm-stage stage1
```

Stage 2, Stage 3 and Full additionally require the preceding stage's generated
`paper_conclusion_verification.json`. For example:

```bash
venv/bin/python run_official_geo_replication.py \
  --stage stage2 \
  --subjective \
  --confirm-stage stage2 \
  --prior-report replication_artifacts/STAGE1_ID/paper_conclusion_verification.json
```

The runner rejects a skipped stage, a failed prior stage, or a report whose stage
identity does not match the expected predecessor.

Resume an interrupted experiment without creating another experiment:

```bash
venv/bin/python run_official_geo_replication.py \
  --experiment-id EXPERIMENT_ID \
  --subjective \
  --confirm-stage resume
```

Cost estimates expose call count, input/output token assumptions, estimated USD cost, and runtime at 60 requests/minute. They are planning estimates, not quotes. Current price assumptions are recorded in code and must be reviewed when provider prices or model availability changes.

## Automatic evidence package

Every completed stage exports:

- `runs.csv`: sample-level provenance and metrics.
- `replication.json`: complete experiment representation.
- `paper_metrics.csv`: paper-oriented statistics on the 0–100 scale.
- `paper_objective_metrics.csv`: PAWC strategy summary.
- `paper_objective_metrics.png`: PAWC comparison chart.
- `paper_conclusion_verification.csv`: one evidence row per paper claim.
- `paper_conclusion_verification.json`: machine-readable claims, trend similarity, fidelity dimensions and stage decision.
- `ReplicationReport.md`: human-readable summary, conclusion verification and confidence scores.

## Fidelity dimensions

- **Method Fidelity:** protocol agreement with the main paper experiment.
- **Implementation Fidelity:** completeness and integrity of persisted runs/evaluations/statistics.
- **Dataset Fidelity:** agreement with the public official benchmark, explicitly accounting for three incomplete rows.
- **Evaluation Fidelity:** objective and seven-dimensional calibrated subjective metric availability.
- **Trend Fidelity:** fraction of testable paper conclusions that pass at the current stage.
- **Model Fidelity:** reported as unknown because the historical checkpoint is unavailable; it is never converted into a misleading numeric penalty.

## Scientific claim policy

Before a stage completes, the only valid claim is that the platform implements the protocol. After a stage passes, the claim must name its sample size. The broad statement that the implementation reproduces the paper's qualitative conclusions is permitted only after the full stage passes its gate. Secondary rank, domain, pairwise, and Perplexity conclusions remain excluded until their explicitly separate protocols are implemented and executed.
