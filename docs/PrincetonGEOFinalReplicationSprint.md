# Princeton GEO Final Replication Sprint

Validation date: 2026-08-20

Primary references:

- Paper (arXiv v3): https://arxiv.org/html/2311.09735
- Official code: https://github.com/GEO-optim/GEO
- Official dataset: https://huggingface.co/datasets/GEO-Optim/geo-bench
- Evaluator prompts pinned to commit: `c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888`

## Prioritized gap analysis

### Critical — implemented in this sprint

1. **Seven-dimensional Subjective Impression was absent.** The evaluator now uses the seven official prompt files (relevance, influence, uniqueness, diversity, follow-up, subjective position and subjective count), the published `gpt-3.5-turbo-instruct` completions configuration, top-5 token log probabilities, and the official probability-weighted 1–5 conversion. Each facet and its raw mean are persisted per sample. Each dataset-level facet is linearly calibrated to the PAWC population mean and variance; their calibrated average is then persisted and included in statistics and exports.
2. **No crash-safe benchmark executor existed.** The official runner now persists each query, generation, evaluation and metric independently. Its resume key is `(experiment_id, experiment_query_id, strategy, sample_index)`, so restarting skips completed samples and begins at the first missing sample.
3. **One-query evidence did not prove benchmark operability.** The runner can plan and execute all 997 valid public test rows, all ten main-experiment strategies and five responses per strategy. A full run is not represented as completed until all samples have been persisted.

### High — implemented in this sprint

1. **Dataset integrity was implicit.** The cached public test file was audited: 1,000 ordered JSONL rows exist; 997 rows are runnable with a complete Top-5; three incomplete rows are rejected rather than repaired; `sugg_idx` selects the published target source. The public repository describes 8,000/1,000/1,000 train/validation/test splits, while this runner deliberately consumes only the official test split used for reporting.
2. **Paper-oriented outputs were incomplete.** Every run exports sample-level CSV/JSON, strategy/metric summary CSV, objective PAWC CSV and a publication-size PNG. The generated Markdown report records data, provider, model, strategies, completion counts, fidelity dimensions and known deviations.
3. **Model differences were not separated from methodological differences.** Reports now distinguish methodological, model, result and trend fidelity.

### Medium — deliberately not implemented now

1. Figure 4 pairwise combinations of four methods on 200 examples.
2. Rank-stratified and tag-stratified paper tables.
3. All-source simultaneous optimization and token-level qualitative diff rendering.
4. Historical Perplexity file-upload/source-restricted protocol.

These extend secondary paper experiments. They do not block running the main GEO-bench baseline-plus-nine-method experiment, but they do block a claim that every experiment in the paper has been reproduced.

### Low — deliberately not implemented now

1. Redrawing conceptual Figures 1–3, which are explanatory illustrations rather than computed experimental figures.
2. UI presentation for replication artifacts. The command-line artifacts are the reproducible source of record.

## Official Subjective Impression procedure

The public code provides all seven evaluator prompts. For each generated answer, each prompt receives the query, answer and selected source rank. The evaluator requests at most three tokens from `gpt-3.5-turbo-instruct` at temperature 0 with five token log probabilities. It converts each returned top token to a bounded 1–5 value; a nonnumeric token receives 1, exactly as the public `convert_to_number` behavior. The score is the probability-weighted expected value across all returned top tokens.

The seven facet scores are stored independently and averaged into a raw Subjective Impression diagnostic. Across aligned completed samples, every facet vector is independently transformed to have PAWC's population mean and variance. The mean of those seven calibrated facets is stored as `subjective_impression_calibrated`. No missing prompt, facet or score is synthesized.

Internally, normalized objective and calibrated subjective scores remain ratios. Paper-oriented exports multiply them by 100 to match Table 1's display scale (for example, the paper's baseline PAWC is 19.3 rather than 0.193).

Important public-code limitation: the repository's historical evaluator returns a cached value and returns zero on a cache miss before reaching its live API code. The authors' complete historical cache is not public. The platform therefore reproduces the disclosed live procedure, not the unavailable cached judgments.

## Dataset audit

| Check | Evidence | Result |
|---|---|---|
| Public test rows | Local official `test.jsonl` line count | 1,000 |
| Complete Top-5 rows | Rows with at least five usable sources | 997 |
| Incomplete rows | Rows not silently repaired | 3 |
| Target selection | Zero-based `sugg_idx`, converted to citation rank 1–5 | Preserved |
| Ordering | Sequential JSONL scan; invalid rows skipped in place | Preserved among runnable rows |
| Main experiment methods | Baseline plus nine official methods | 10 |
| Responses per query/method | Public runner and paper protocol | 5 |

## Execution scale and budget boundary

The largest directly runnable public main experiment requires:

- 997 queries × 10 strategies × 5 answers = **49,850 answer generations**.
- 997 queries × 9 rewritten strategies = **8,973 rewrite generations** (rewrites are reused for the five answers).
- With Subjective Impression: 49,850 answers × 7 facets = **348,950 judge calls**.
- Total provider calls with subjective evaluation: **407,773**.

Launching that paid workload requires an explicit execution budget and runtime approval. The CLI prints this plan before execution and supports resuming by experiment ID. Lack of a paid full run is an evidence limitation, not a hidden implementation failure.

## Fidelity assessment

| Dimension | Status | Meaning |
|---|---|---|
| Methodological Fidelity | High for the main experiment | Official data, target mapping, methods, answer count, objective metrics and disclosed subjective procedure are implemented. |
| Model Fidelity | Partial | Current `gpt-3.5-turbo`, `gpt-3.5-turbo-16k` and `gpt-3.5-turbo-instruct` aliases are not immutable 2023 checkpoints. |
| Result Fidelity | Not established | Requires the complete paid run and comparison with paper tables. |
| Trend Fidelity | Not established | Requires the complete paid run and strategy-order/effect comparison. |

**Operational readiness for the main GEO-bench replication: 87%.** This is a capability/readiness assessment, not a result-reproduction score. The remaining 13% reflects historical model/cache unavailability and the unexecuted full benchmark. Readiness must not be interpreted as 87% numerical agreement.

## Honest replication claim

The platform can honestly claim that it implements a reproducible, crash-safe replication workflow for the paper's **main public GEO-bench experiment**. It cannot yet claim that it has reproduced the paper's reported results: no complete 997-query paid run has been executed, exact historical model snapshots and subjective caches are unavailable, and the secondary pairwise/Perplexity experiments remain out of scope for this sprint.

The claim becomes evidence-backed only after `run_official_geo_replication.py --subjective` completes, all expected runs and calibrated evaluations are present, exports are generated, and the generated report compares aggregate results and trends against the published tables.
