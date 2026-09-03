# GEO Predictor Dataset Pipeline

## Scope

This phase creates a machine-learning-ready dataset pipeline. It does not train,
load, or execute a predictive model. Existing GEO generation, evaluation, and
replication behavior remains authoritative and unchanged.

## Architecture

```text
OfficialReplicationRunner / ExperimentService
                    │
                    ▼
        ExperimentRepository.mark_completed
                    │ scientific transaction commits first
                    ▼
        DatasetBuilder.collect_completed_experiment
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
 validate completed run   resolve provenance
 and required metrics     query/document/prompt
          └─────────┬─────────┘
                    ▼
       immutable TrainingSample snapshot
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
    summary API          CSV / JSONL export
          │                   │
          └─────────┬─────────┘
                    ▼
            GEO Predictor page
```

## Data flow

1. The existing experiment runner generates answers and persists evaluations.
2. `ExperimentRepository.mark_completed` commits the experiment result.
3. After that commit, `DatasetBuilder` loads completed `ExperimentRun` rows.
4. The builder joins each run to its query, selected source document, strategy
   result, prompt version, and evaluation metrics.
5. A unique `experiment_run_id` makes collection idempotent. Resuming or
   re-finalizing an experiment cannot create duplicate samples.
6. Complete samples are written as immutable snapshots. A collection failure is
   logged but cannot change a successfully completed experiment into a failed run.

## Training sample lifecycle

```text
Experiment running
      ↓
Answers and evaluations persisted
      ↓
Experiment completed and committed
      ↓
Source run validated
      ↓
TrainingSample inserted once
      ↓
Available to summary and export APIs
```

Rows cannot be updated or deleted through the SQLAlchemy model. Snapshot fields
are deliberate: they keep exported datasets reproducible while foreign-key IDs
preserve direct traceability to the operational experiment records.

## Validation rules

Exports exclude samples missing any required provenance, source text, generated
answer, provider/model identity, or core objective metric. Subjective score is
optional because subjective evaluation is an experiment option. The summary API
reports stored rows, valid rows, invalid rows, and missing-field counts separately.

## API

- `GET /predictor/dataset` returns dataset counts, coverage, health, and latest
  sample time.
- `GET /predictor/dataset/export?format=csv` returns clean CSV records.
- `GET /predictor/dataset/export?format=jsonl` returns clean newline-delimited JSON.

## Export format

Each row contains:

- Experiment, run, and query identifiers
- Query, strategy, and sample index
- Original and modified source documents
- Exact generation prompt and generated answer
- Visibility, citation, subjective, PAWC, word, and position metrics
- Provider, model, dataset, and prompt-version provenance
- Sample creation timestamp

CSV is suitable for dataframe and warehouse ingestion. JSONL preserves long text
without requiring a nested document format and can be streamed one record at a
time. The illustrative schema record in
`docs/examples/geo_predictor_training_sample.example.jsonl` is documentation
only and is never returned by the API.

## Future extension points

- Dataset version manifests and checksums
- Train/validation/test split manifests
- Provenance-aware filtering by experiment or dataset version
- Additional validated target metrics
- A separately approved feature-engineering layer
- A separately approved model-training consumer

Future model code should consume the clean CSV or JSONL export rather than query
operational experiment tables directly. This keeps scientific provenance and
dataset validation independent from any modeling framework.
