# Princeton GEO Replication Validation

> Historical baseline (55%) from before the final replication sprint. For the
> current implementation, gap status and evidence, see
> `docs/PrincetonGEOFinalReplicationSprint.md`. Statements below that mark the
> subjective evaluator or full-benchmark runner as missing are retained as the
> pre-sprint audit trail and are no longer current.

Validation date: 2026-08-20  
Reference: Aggarwal et al., *GEO: Generative Engine Optimization*, arXiv v3 / KDD 2024.  
Primary implementation reference: `GEO-optim/GEO` public repository.

## Verdict

**Overall replication readiness: 55%.**

The platform can run the paper's core objective-impression experiment for a GEO-bench query using the published target source, official strategy prompts, GPT-3.5, five generated answers, PAWC/Word/Position metrics, statistics, and CSV export. It cannot reproduce the complete paper because Subjective Impression, pairwise strategy combinations, tag-stratified analysis, all-source optimization, and the paper's Perplexity file-upload protocol are missing. A full 1,000-query numerical match is also impossible from the current public split without an explicit policy for three rows that do not contain five sources and without the original dated model snapshots/caches.

The percentage is an equal-weight readiness score across 20 executable requirements: 8 correct, 6 partial, 6 missing/incorrect (`8 + 0.5×6 = 11/20`). It measures workflow readiness, not agreement with the paper's reported values.

## Structured replication checklist

| Paper component | Paper requirement | Platform status | Validation |
|---|---|---|---|
| Main GEO experiment | Complete 1,000-query test split, baseline + nine methods | Partial | All ten methods exist, but only 997 public rows have Top-5 sources and subjective evaluation is absent. |
| GEO-bench | 10K total; 8K/1K/1K splits; nine source datasets; Top-5 cleaned Google results and tags | Partial | Official 1,000-row test JSONL is cached. It contains queries, sources, tags and `sugg_idx`; three rows have fewer than five sources. Train/validation are not locally managed. |
| Optimization target | One randomly selected source, fixed across methods for a query | Implemented | Loader now honors published zero-based `sugg_idx`; target rank stays fixed across methods and repeated responses. |
| Answer generation | GPT-3.5-turbo, Top-5, no summarization, temperature 0.7, five responses | Implemented with temporal limitation | Prompt and parameters match. Current API alias is not the immutable 2023 model snapshot. |
| Baseline | Unmodified selected source | Implemented | `original` passes source through unchanged. |
| Nine GEO methods | Official prompts and independent application to the same source | Implemented | Strategy prompt text and rewrite settings match public `geo_functions.py`. |
| Rewrite model | GPT-3.5-turbo-16k, temperature 0, top_p 1, max_tokens 3192 | Implemented with temporal limitation | Parameters match and model was callable during validation. Snapshot is not pinned. |
| PAWC | Official normalized position-adjusted word count | Implemented | Citation parsing, word filter, shared-credit rule, exponential decay and response normalization match public `utils.py`. |
| Word submetric | Official normalized cited word count | Implemented | Previously computed only as raw count; normalized score is now collected independently. |
| Position submetric | Official normalized position count | Implemented | Function existed but was unused; it is now collected independently. |
| Subjective Impression | Seven G-Eval facets, repeated scoring and calibration to PAWC mean/variance | Missing | No relevance, influence, uniqueness, diversity, follow-up/click, subjective position or subjective count evaluator. No score is fabricated. |
| Relative improvement | `(modified − baseline) / baseline × 100` | Implemented | Previous backend used absolute difference while UI said relative. Corrected; zero baselines return unavailable rather than invented zero. |
| Five random seeds | Five experimental repetitions and reported average/deviation | Partial | Platform repeats five times and samples five answers per method. Exact paper seeds and seed-control mechanism are not published; OpenAI seed is not provided by the legacy paper code. |
| Statistical deviation | Mean across runs with deviation | Partial | Mean/std are available. Extra median/variance/CI are platform diagnostics, not claimed as paper statistics. The paper does not define whether `±` is SD, SE, or CI; therefore no equivalence claim is made. |
| Rank analysis | Aggregate relative improvement by target SERP rank 1–5 | Partial | Target rank and required metrics are now available, but no dedicated Table 2 aggregation/export exists. |
| Domain/tag analysis | Aggregate top-performing methods by GEO-bench categories | Missing | Tags remain in input metadata and are not propagated into run-level exports. |
| Multiple-site optimization | Optimize all source contents simultaneously | Missing | Current execution optimizes exactly one target source. |
| Pairwise combinations | All pairs of Cite, Fluency, Statistics and Quotation on 200 examples | Missing | Current strategy execution is independent; it does not compose two rewrites sequentially. |
| Qualitative examples | Modified source with additions/deletions and relative improvement | Partial | Original/modified text and metric values are stored, but no token-level diff export is generated. |
| Perplexity in the wild | 200 examples uploaded as files; answers restricted to uploaded files | Incorrect methodology | Current Perplexity adapter submits a text prompt. It does not reproduce file upload or source restriction. |

## Strategy validation

| Platform strategy | Paper/public-code method | Result |
|---|---|---|
| `original` | `identity` | Exact logic. |
| `statistics` | `stats_optimization_mine` | Prompt matches, including the official wording and output format. |
| `citation` | `citing_credible_sources_mine` | Prompt matches. |
| `quotation` | `more_quotes_mine` | Prompt matches. |
| `authoritative` | `authoritative_optimization_mine` | Prompt matches. |
| `easy_to_understand` | `simple_language_mine` | Prompt matches. |
| `fluency` | `fluent_optimization_gpt` | Prompt matches. |
| `unique_words` | `unique_words_optimization_gpt` | Prompt matches. |
| `technical_terms` | `technical_terms_mine` | Prompt matches. |
| `keyword_stuffing` | `seo_optimize_mine2` | Prompt matches. |

The platform applies methods independently, as required for the main experiment. It does not implement the separate pairwise-combination experiment.

## Metric equivalence

| Metric visible in platform | Paper metric? | Equivalence |
|---|---|---|
| PAWC / visibility score | Yes | Equivalent to public `impression_wordpos_count_simple` for the selected source. “Visibility” is only a UI alias for PAWC in this workflow. |
| Word score | Yes | Equivalent after this validation correction. |
| Position score | Yes | Equivalent after this validation correction. |
| Citation count | Diagnostic only | The paper does not use raw citation count as its headline impression metric. Do not compare it with Table 1. |
| First citation position | Diagnostic only | Not equivalent to the paper's normalized Position submetric. |
| Brand mention | No | Belongs to the separate platform benchmark/citation workflow, not Princeton GEO reproduction. |
| Average position/ranking | Only for stratifying by selected search rank | It is not a substitute for PAWC. |
| Coverage | No | Operational completion coverage, not a paper visibility metric. |
| Subjective Impression | Yes | Missing. |

## Paper figures and tables

| Artifact | Required data | Can platform generate it now? |
|---|---|---|
| Figure 1 | Conceptual before/after illustration | Not a data figure; no CSV applicable. |
| Figure 2 | Conceptual GE architecture | Not a data figure; no CSV applicable. |
| Figure 3 | Explanatory visibility example | PAWC/Word/Position data: yes. Subjective facets: no. |
| Figure 4 | 4×4 pairwise-strategy relative-improvement heatmap on 200 rows | No; combined-strategy execution is missing. |
| Table 1 / 6 | Absolute Word, Position, PAWC and seven subjective metrics for baseline + methods | Partial CSV: objective metrics yes; seven subjective columns missing. |
| Table 2 | Relative PAWC improvement grouped by selected rank | Data available after target fix; dedicated aggregate CSV missing. |
| Table 3 | Top methods by tag/category | No; tag provenance is not included in result exports. |
| Table 4 | Representative source diffs and improvements | Partial; raw before/after exists, diff markup missing. |
| Table 5 / 7 | Perplexity file-grounded results on 200 samples | No; current provider methodology differs. |

## End-to-end validation run

A real, non-mocked run completed using the configured OpenAI provider:

- Dataset: official GEO-bench test split.
- Query: `mention the names of any 3 famous folklore sports in karnataka state`.
- Published target: `sugg_idx=3`, therefore citation/source rank 4.
- Methods: No Optimization and Statistics Addition.
- Answer model: `gpt-3.5-turbo`.
- Rewrite model: `gpt-3.5-turbo-16k`.
- Temperature: 0.7; top_p: 1.
- Five generated answers per method; ten evaluated sample rows.
- Baseline mean PAWC: 0.04.
- Statistics Addition mean PAWC: 0.08.
- Relative improvement for this single query: 100%.

This single-query outcome validates plumbing only. It is not evidence that the paper's aggregate effect size was reproduced.

Artifacts:

- `verification_artifacts/research_validation/single_query_samples.csv`
- `verification_artifacts/research_validation/single_query_summary.csv`
- `verification_artifacts/research_validation/run_manifest.json`

## Known deviations and limitations

1. The public repository's Subjective Impression path depends on cached G-Eval outputs and legacy `gpt-3.5-turbo-instruct` log probabilities. The checked-in public function returns zeros on cache miss before its live evaluation code, so the published repository alone is insufficient to regenerate all subjective scores without the authors' cache/procedure clarification.
2. Current GPT-3.5 aliases may differ from the model snapshots used in 2023–2024. Exact numerical reproduction cannot be claimed without immutable model identifiers or original cached generations.
3. The paper reports five random seeds but does not publish the numeric seeds or fully define the displayed statistical deviation. The platform can repeat the experiment but cannot prove identical randomness.
4. Three rows in the current official test JSONL do not contain five sources. The platform correctly refuses to invent missing sources, leaving 997 directly runnable rows.
5. Perplexity's historical file-upload behavior and model version are not reproducible through the current text API integration.
6. The full main experiment is expensive: approximately 1,000 queries × 10 methods × 5 responses × 5 repetitions, plus rewrite calls. It was not launched merely to produce incomplete objective-only results.

## Replication decision

The platform is ready for **objective-metric pilot replications**, not for a claim of full-paper reproduction. A valid full replication requires, at minimum: the seven subjective evaluators and calibration procedure, combined-strategy execution, tag propagation, all-source optimization, a faithful Perplexity file-upload protocol or an explicitly scoped exclusion, and a documented policy for the three malformed public rows.
