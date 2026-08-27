# Princeton GEO Experiment Architecture Audit

## Goal

The platform's research lifecycle is:

`Property → Dataset Version → Experiment Definition → Runs → Evaluations → Metrics → Statistics → Comparison → History → Export`

An experiment is the immutable definition of what should be tested. A run is one provider/model/strategy/query/seed/sample execution. Evaluation is a separate, versioned operation over a completed run. Metrics are individual observations, not fields inferred from UI labels. Statistics are derived, persisted summaries that can always be rebuilt from metrics.

## Current-state audit

| Lifecycle stage | Status before P0 | Evidence and gap |
|---|---|---|
| Property | Working | Experiments, campaigns, datasets and benchmarks can be property-scoped. |
| Dataset/question set | Partial | Manual, CSV and GEO-bench inputs work. `BenchmarkDataset` was mutable and unversioned; Experiment Lab also stored dataset input as JSON. |
| Strategy selection | Working | The ten Princeton strategies are validated; paper mode adds the original baseline. |
| Prompt generation | Partial | Full prompt text was stored, but the template had no version identity. |
| LLM execution | Partial | Provider/model/config execution worked, but Experiment represented both definition and execution and token metadata was not captured. |
| Evaluation | Partial | Princeton citation/PAWC evaluation worked but ran inline inside generation. Brand-mention benchmark heuristics were mislabeled as citation and visibility metrics. |
| Metric collection | Partial | A few values existed on strategy-result rows and in JSON, with no metric provenance or extensible metric layer. |
| Statistical analysis | Partial | Campaign serialization calculated mean/std in memory. Median, variance, confidence interval, min/max, and persisted summaries were absent. |
| Benchmark comparison | Partial | Strategy ranking and baseline deltas existed for a single campaign/provider. The separate Benchmark subsystem executed only its first configured provider. |
| Experiment history | Partial | Campaign status and benchmark history existed, but no complete experiment lifecycle timeline. |
| Export | Partial | Campaign JSON/CSV worked. Individual experiment export, PNG charts and a report were absent. |
| Reproducibility | Missing | No immutable prompt/dataset version linkage, duplicate/run-again endpoint, or per-sample run identity. |

Only the functions above verified in code were counted as working. UI placeholders and stored configuration without an executable path were not counted.

## P0 implemented

- `Experiment` remains the compatible experiment definition and now records dataset version, prompt version, generation parameters, status and run count.
- `ExperimentRun` records every query/strategy/seed/sample execution, raw prompt/response, provider/model, latency, token fields, cost field and status.
- `ExperimentEvaluation` records evaluator identity/version independently of generation.
- `ExperimentMetric` records each observed value with unit, optional confidence and metadata.
- `ExperimentStatistic` persists count, mean, median, variance, standard deviation, 95% normal-approximation confidence interval, minimum and maximum per strategy/metric.
- `ExperimentPromptVersion` stores the exact templates and checksum. Existing prompt construction remains unchanged.
- `BenchmarkDataset` records type, version, content checksum and frozen state for newly created datasets.
- `ExperimentEvent` stores configured, execution started, statistics completed, completed and failed timeline events.
- Existing strategy result rows link to the new run records, preserving the current frontend contract.
- Experiment list/detail, duplicate-and-run, JSON export and CSV export APIs are available under `/api/v1/experiment-lab/experiments`.
- The legacy benchmark UI no longer labels a brand mention as a citation or reports a fabricated visibility score. It exposes brand mention rate and average observed position.

Token and cost columns intentionally remain `null` until provider adapters return authoritative usage. Null means “not observed”; it is never replaced with an estimate or zero.

## P1

- Execute every selected provider/model combination, with provider failures isolated by run.
- Add experiment comparison UI with baseline deltas, confidence intervals and distribution charts.
- Add dataset and prompt-version management screens and explicit immutable-version selection.
- Capture authoritative provider token usage and versioned pricing for cost.
- Add PNG/SVG chart export and a generated research report.
- Backfill legacy Experiment Lab results into runs/metrics where provenance is sufficient.

## P2

- Pluggable asynchronous evaluators for answer quality, factuality, citation validity and calibrated confidence.
- Campaign-level orchestration across datasets, providers and parameter sweeps.
- Paired tests, bootstrap intervals, multiple-comparison correction and cross-dataset meta-analysis.
- Publication bundles with environment manifests, source snapshots and signed checksums.

## Compatibility and migration

Migration `20260820_0016` is additive. Existing experiment, campaign and strategy-result tables and API response fields remain intact. New executions populate both the compatibility result and the normalized research records. Existing records remain readable; they are not assigned invented provenance. A future P1 backfill may normalize only fields that can be derived exactly.

The Benchmark subsystem remains separate during P0 to avoid breaking dashboard and history behavior. Its trustworthy observed metrics were relabeled; unverified citation/visibility heuristics were removed from new summaries. Converging Benchmark onto the unified run/evaluation/metric tables is P1 because it requires multi-provider orchestration and historical migration policy.
