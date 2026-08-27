# Princeton GEO Platform Integration

The current Experiment Lab is a web client for the existing official Princeton GEO replication pipeline. The scientific implementation remains in `OfficialReplicationRunner`; no prompts, strategies, evaluation formulas, datasets, or report generators are duplicated in the frontend or API layer.

## Shared execution path

Both clients use `OfficialReplicationService`:

```text
CLI or Experiment Lab
        ↓
OfficialReplicationService
        ↓
OfficialReplicationRunner
        ↓
existing experiment tables + replication_artifacts/{experiment_id}
```

The service only creates/resumes a run, invokes the existing runner, exports the existing artifacts, and reads those records and files for the UI.

## Web workflow

Open **Experiment Lab**, then use **Princeton GEO Replication**:

1. Select Stage 1, Stage 2, Stage 3, or Full.
2. Choose whether to enable the existing subjective evaluator.
3. Optionally enter an experiment name.
4. Click **Run Experiment**.

The page polls the existing experiment record for status, current query, current strategy, completed queries, elapsed time, and estimated remaining time. Completed runs expose only artifacts that already exist on disk, including the replication report, conclusion verification, CSV, JSON, and generated figures.

The same panel lists previous official replication runs with their stage, creation time, status, runtime, recorded trend similarity, and stage decision. Selecting **Open Result** changes the active record without creating or recomputing anything.

Summary indicators and figure previews are read from the generated paper-conclusion JSON and existing PNG files. Claim counts and fidelity values are displayed only when those generated outputs contain them.

Missing values are displayed as **Not recorded**. The frontend does not infer costs, claims, or scientific metrics.

## API

- `POST /api/v1/experiment-lab/official-replications`
- `GET /api/v1/experiment-lab/official-replications`
- `GET /api/v1/experiment-lab/official-replications/{experiment_id}`
- `GET /api/v1/experiment-lab/official-replications/{experiment_id}/artifacts/{path}`

The polling response intentionally omits sample-level prompts and answers because the page consumes aggregate state and generated artifacts. This avoids repeatedly transferring the full experiment corpus while a run is active.

## CLI

`run_official_geo_replication.py` now calls the same `OfficialReplicationService`. Existing confirmation and prior-stage checks remain in the CLI, while scientific execution remains exclusively in `OfficialReplicationRunner`.
