# Princeton GEO Scientific Provenance Audit

**Audit date:** 2026-08-20  
**Scope:** source-level scientific provenance of the platform's Official Princeton GEO Replication Runner  
**Audit mode:** read-only; no experiment or application source was changed  
**Verdict:** **YES, WITH DISCLOSED MODERN MODEL DIFFERENCES**

## Executive summary

The replication is recognizably and substantially an implementation of the methodology published in *GEO: Generative Engine Optimization*. Its core experimental path uses the official GEO-bench test artifact, the official ten conditions (baseline plus nine GEO methods), the official rewrite instructions, the official answer prompt, one rewrite per query/strategy, one `n=5` answer request, and direct ports of the paper's citation-based visibility metrics.

It is not an archival, bit-for-bit recreation of the historical experiment. The most consequential reason is model provenance: the runner requests the historical alias `gpt-3.5-turbo-16k`, but a measured contemporary API response identified the answering and rewriting checkpoint as `gpt-3.5-turbo-0125`. The original frozen model weights, backend sampling implementation, and numeric seed are not available through the current API. The subjective evaluator likewise uses the official legacy model name and intended public scoring code, but the public repository's live evaluator path is unreachable without a private cache; the platform therefore reconstructs the intended procedure rather than reproducing the public program's literal cache-miss behavior.

There are three additional disclosures: the local test artifact contains 1,000 records but only 996 satisfy the runner's Top-5/target/content validity rules, while the “full” stage metadata says 997; the dataset download URL is not revision-pinned even though the currently cached file exactly matches a verified Hugging Face revision; and the platform's subjective-score calibration is supported by the paper's description but is not present as executable calibration code in the audited public repository commit.

On balance, an author could reasonably recognize this as the same published methodology, provided results are labeled a **modern model replication**, not an exact historical rerun, and the dataset-count and subjective-calibration qualifications are reported.

## 1. Audit basis and identity of the official artifacts

### 1.1 Paper

| Field | Verified value |
|---|---|
| Title | *GEO: Generative Engine Optimization* |
| arXiv | [2311.09735](https://arxiv.org/abs/2311.09735) |
| Authors | Pranjal Aggarwal; Vishvak Murahari; Tanmay Rajpurohit; Ashwin Kalyan; Karthik Narasimhan; Ameet Deshpande |
| Version used for interpretive comparison | arXiv v3, 2024-06-28; paper states acceptance at KDD 2024 |
| Central experimental artifact | GEO-bench and the GEO methods evaluated with citation-based and subjective visibility measures |

### 1.2 Official implementation

| Field | Verified value |
|---|---|
| Repository | [GEO-optim/GEO](https://github.com/GEO-optim/GEO) |
| Audit commit | [`c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888`](https://github.com/GEO-optim/GEO/tree/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888) |
| Commit date/subject | 2025-10-29, `web` |
| Tags | No release tag identifies this commit as the exact paper snapshot |
| Core files | [`src/run_geo.py`](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/run_geo.py), [`src/generative_le.py`](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/generative_le.py), [`src/geo_functions.py`](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/geo_functions.py), [`src/utils.py`](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/utils.py) |

The commit above is the explicit prompt provenance pinned by the current subjective evaluator. It is the official repository, but it postdates the paper and is not a tagged historical release. It is therefore an authoritative **public reference implementation**, not unquestionable proof of the exact source tree used to produce the paper's numbers.

### 1.3 Dataset

| Field | Verified value |
|---|---|
| Dataset | [GEO-Optim/geo-bench](https://huggingface.co/datasets/GEO-Optim/geo-bench) |
| Audited revision | [`16a179f6bbb08ee7c357797ce8df483c5dd22130`](https://huggingface.co/datasets/GEO-Optim/geo-bench/tree/16a179f6bbb08ee7c357797ce8df483c5dd22130) |
| License | CC-BY-SA-4.0 |
| Stated scale | 10,000 queries with five cleaned responses from top Google results |
| Local artifact | `backend/experiment_dataset/geo_bench/test.jsonl` |
| Byte comparison | Local and pinned `test.jsonl` SHA-256 both `33d721e7e779f9ac71892893680954bc8c5bbc4441effc6e11cc8e8c52ea55a6` |
| Physical test rows | 1,000 |
| Runner-valid test rows | 996: one row lacks usable query text; three have fewer than five usable sources |

The paper, GitHub repository, and Hugging Face dataset are published under the same GEO project identity and cross-reference each other. They are unquestionably related official research artifacts. They are **not unquestionably the same immutable release**: neither repository supplies a paper-era code tag, the audited code commit is later than the paper, and the dataset has an independent revision history.

## 2. Component provenance and comparison

Classification used below:

- **Exact Match** — same effective bytes/parameters/algorithm for the tested path.
- **Equivalent** — an engineering representation differs but preserves the scientific operation.
- **Scientific Difference** — the experimental distribution, inputs, metric, or reported statistic can change.
- **Engineering Difference** — persistence, diagnostics, or output structure differs without changing the intended measurement.

### 2.1 GEO strategies

Official strategy definitions are in [`src/geo_functions.py`](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/geo_functions.py). Current definitions are in [`backend/app/ge/geo_rewriter.py`](../backend/app/ge/geo_rewriter.py). Each comparison was performed after inserting the same sample source and query. “Whitespace-equivalent” means the strings became identical after whitespace normalization; it does not mean byte-identical.

| Condition | Official symbol | Official instruction | Current instruction | Bytes | Classification | Scientific impact |
|---|---|---|---|---|---|---|
| Original | `identity` | Return source unchanged | Return source unchanged | Identical | Exact Match | None |
| Quotation | `more_quotes_mine` | Add quotations from credible sources without changing content | Same | Different; whitespace-equivalent | Equivalent | No semantic difference; whitespace may marginally alter tokenizer input |
| Statistics | `stats_optimization_mine` | Add quantitative statistics without changing meaning | Same | Different; whitespace-equivalent | Equivalent | Same qualification |
| Citation | `citing_credible_sources_mine` | Add citations from credible sources | Same | Different; whitespace-equivalent | Equivalent | Same qualification |
| Fluency | `fluent_optimization_gpt` | Improve fluency without changing content | Same | Identical | Exact Match | None |
| Easy-to-understand | `simple_language_mine` | Simplify language while preserving content | Same | Different; whitespace-equivalent | Equivalent | Same qualification |
| Technical Terms | `technical_terms_mine` | Add relevant technical terminology | Same | Different; whitespace-equivalent | Equivalent | Same qualification |
| Authoritative | `authoritative_optimization_mine` | Use a confident, authoritative style | Same | Different; whitespace-equivalent | Equivalent | Same qualification |
| Unique Words | `unique_words_optimization_gpt` | Increase lexical uniqueness while preserving meaning | Same | Identical | Exact Match | None |
| Keyword Stuffing | `seo_optimize_mine2` | Apply conventional SEO keyword repetition | Same | Different; whitespace-equivalent | Equivalent | Same qualification |

The shared system instruction is semantically and whitespace-normalized identical. The official string contains trailing spaces/newline formatting not retained by the current port. No strategy was substantively rewritten.

### 2.2 Prompt builder

Official source: [`src/generative_le.py`](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/generative_le.py). Current source: [`backend/app/ge/prompt_builder.py`](../backend/app/ge/prompt_builder.py) and runner lines 118–125.

| Element | Official | Current | Result |
|---|---|---|---|
| Answer instruction | One long instruction beginning “Write an accurate and concise answer…” | Same constant | Exact Match |
| Source block | `### Source {i}:\n{source}\n\n\n` | Same rendered block | Exact Match |
| Source order | Input list order | GEO-bench first five, original order | Exact Match |
| Numbering | 1 through 5 | Document rank 1 through 5 | Exact Match |
| Question suffix | `### Question: {query}` plus answer cue | Same | Exact Match |
| System message | None; entire prompt is a user message | `system_prompt=""`; provider omits empty system message | Exact Match |
| Replaced source | Replace the source selected by `sugg_idx` before formatting | Replace document at `selected_rank` with rewrite | Exact Match |

An automated sample comparison produced a byte-identical final answer prompt. The local constant name `GE_SYSTEM_PROMPT` is misleading, but its value is placed in the user message exactly as in the official code; this is naming only.

### 2.3 Answer generation

| Parameter | Official `generative_le.py` | Current runner/provider | Classification |
|---|---|---|---|
| Endpoint | Chat Completions | Chat Completions | Exact Match |
| Requested model | `gpt-3.5-turbo-16k` | `gpt-3.5-turbo-16k` | Exact request; Scientific Difference at runtime |
| Observed current model | Not recorded by official code | `gpt-3.5-turbo-0125` in the measured profile | Scientific Difference |
| Temperature | 0.5 | 0.5 | Exact Match |
| `top_p` | 1 | 1 | Exact Match |
| `max_tokens` | 1024 | 1024 | Exact Match |
| `n` | 5 | 5 in one API request | Exact Match |
| Stop | Not specified | Not specified | Exact Match |
| Frequency/presence penalties | Not specified, API defaults | Not specified, API defaults | Exact Match |
| Seed | Not specified | Not specified | Exact Match; nondeterministic API sampling remains |
| Choice order | API choice order | Explicit sort by API choice index | Equivalent |
| Answer suffix | Newline appended | Newline appended | Exact Match |

Current call path: `OfficialReplicationRunner.execute` → `OpenAILLMRunner.generate_many` → `ChatGPTProvider.generate_texts` → `chat.completions.create(n=5)`. The five choices are generated before any choice is evaluated.

The request is faithful to the public code, but the service-side historical checkpoint is not reproducible. The alias/model-routing difference can change wording, citation behavior, variance, and all downstream metrics. This is the largest remaining scientific limitation.

### 2.4 Rewrite generation

Official path: `run_geo.py` → strategy function → `geo_functions.call_gpt`. Current path: runner lines 111–117 → [`GeoRewriter.rewrite`](../backend/app/ge/geo_rewriter.py).

| Behavior | Official | Current | Result |
|---|---|---|---|
| Frequency | Once for a query/strategy, then reused by its five answers | Once for a query/strategy, then reused by its five answers | Exact Match |
| Model request | `gpt-3.5-turbo-16k` | Same | Exact request; runtime model difference |
| Temperature | 0 | 0 | Exact Match |
| `top_p` | 1 | 1 | Exact Match |
| `max_tokens` | 3192 | 3192 | Exact Match |
| Cache key | String representation of user/system prompts | Content-derived user/system key | Equivalent |
| Reuse | Cached rewrite reused | Persisted rewrite/batch reused | Equivalent |
| Resume | JSON cache and answer cache | Database status and generated-batch resume | Engineering Difference |

The official baseline is effectively reused: although `identity` appears in the method loop, the answer cache resolves the unchanged source list, so it does not establish a second scientifically distinct baseline sample. The current runner produces one baseline batch. This is equivalent.

### 2.5 Dataset loader

Current loader: [`backend/app/experiment/geo_bench_loader.py`](../backend/app/experiment/geo_bench_loader.py).

| Feature | Official artifact/paper | Current | Classification |
|---|---|---|---|
| Dataset identity | `GEO-Optim/geo-bench` | Same | Exact Match |
| Test artifact | Hugging Face `test.jsonl` | Byte-identical local copy at audited revision | Exact Match at audit time |
| Download version | Dataset revision exists | URL uses `resolve/main/test.jsonl` | Engineering Difference with future reproducibility risk |
| Query count | Public test file has 1,000 physical rows | Loads 1,000 before validation | Exact Match |
| Valid query count | Not explicitly resolved by public runner | 996 accepted; stage metadata says 997 | Scientific Difference |
| Sources | Five stored result objects | First five usable source objects | Exact for valid rows |
| Source order | Stored order | Preserved | Exact Match |
| Target | `sugg_idx` | `sugg_idx + 1` rank | Exact Match |
| Text selection | Dataset supplies `cleaned_text` and `raw_text` | `cleaned_text`, else `raw_text`, then strip | Equivalent for audited valid rows; fallback may differ if fields change |
| Retrieval | Paper describes fixed relevant sources; dataset supplies five cleaned web responses | No live retrieval in official runner path | Methodologically appropriate |
| Train/validation | Part of 10k corpus | Not downloaded/used by this test runner | Intentional omission; no impact on test-only experiment |

The public `run_geo.py` loads the Hugging Face test split but its visible `improve(query, idx)` path does not directly pass the row's source objects to answer generation; it can fall back to search/cache behavior. Consequently, the public code and dataset artifact do not form a completely self-contained historical rerun. The platform's direct use of the official fixed Top-5 passages is more consistent with the paper's controlled experiment description, but is not execution-identical to that public call path.

### 2.6 Objective evaluation

Official formulas are in [`src/utils.py`](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/utils.py); current port is [`backend/app/evaluation/evaluator.py`](../backend/app/evaluation/evaluator.py).

| Component | Comparison | Classification | Note |
|---|---|---|---|
| Citation extraction | Same bracketed-integer regex and citation list semantics | Exact Match under NLTK path | Hallucinated indices are ignored after diagnostic output |
| Word count | Same token filter: token length greater than two | Exact Match under NLTK path | Uses NLTK sentence/word tokenization |
| PAWC | Same cited-word contribution, exponential sentence-position decay, shared-citation division, and normalization | Exact Match | Selected source indexed by `sugg_idx` rank |
| Word score | Same word-only contribution and normalization | Exact Match | Also stores raw selected cited-word count |
| Position score | Same exponential position contribution and normalization | Exact Match | Same zero-citation uniform fallback |
| Tokenizer failure | Official assumes NLTK; current falls back to regex tokenizers | Scientific Difference when fallback is activated | Sentence boundaries and word counts can change |
| Stored precision | Official calculations retain float precision; current stores selected ratios rounded to six decimals | Scientific Difference, negligible magnitude | Can affect last digits of aggregate results |

The fallback is a resilience feature, not proof of scientific equivalence. A faithful run should record that NLTK resources were present so the fallback was not used.

### 2.7 Subjective Impression

Official source: seven files under [`geval_prompts/`](https://github.com/GEO-optim/GEO/tree/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/geval_prompts) plus intended evaluator code in `src/utils.py`. Current source: [`backend/app/evaluation/subjective_evaluator.py`](../backend/app/evaluation/subjective_evaluator.py).

| Element | Official | Current | Classification |
|---|---|---|---|
| Dimensions | relevance, influence, uniqueness, diversity, follow-up, subjective position, subjective count | Same seven | Exact Match |
| Prompt bytes | Seven repository text files | Fetched from pinned commit and used verbatim, with the same query/answer/rank substitutions | Exact Match |
| Calls | One completion call per dimension | One completion call per dimension | Exact Match to intended code |
| Model | `gpt-3.5-turbo-instruct` | Same requested model | Exact request; historical service behavior not frozen |
| Temperature / max tokens / `top_p` | 0 / 3 / 1 | 0 / 3 / 1 | Exact Match |
| Penalties / logprobs / `n` | 0 / 0 / 5 / 1 | 0 / 0 / 5 / 1 | Exact Match |
| Stop | Explicit `None` | Omitted, API default | Equivalent |
| Score conversion | Clamp numeric tokens to 1–5; nonnumeric → 1 | Same | Exact Match |
| Probability weighting | Normalize `exp(logprob)` mass and calculate expected score | Same | Exact Match |
| Raw composite | Mean of seven dimension scores | Same | Exact Match |
| Calibration | Paper describes matching subjective distribution to objective scale; no executable calibration was located in audited public commit | Each facet is population mean/variance matched to PAWC, then averaged | Scientific provenance gap |
| Cache | Public code expects a separate evaluator cache | DB stores completed metrics but no equivalent prompt-result cache | Engineering Difference |

Critical public-code caveat: on a subjective cache miss, the audited `src/utils.py` returns zero-valued results before the live evaluator block. That makes the live block unreachable, and the referenced complete evaluator cache is not part of the public repository. The platform executes the apparent intended algorithm. This is scientifically defensible as a reconstruction of the paper's procedure, but it is not a literal behavioral copy of the public cache-miss path.

The calibration formula is plausible and consistent with the paper's stated scale matching, but its exact facet-by-facet placement cannot be verified against executable official code. Raw seven-facet results should therefore remain available in reports alongside calibrated results.

### 2.8 Experiment protocol, persistence, and statistics

| Protocol element | Official | Current | Classification |
|---|---|---|---|
| Query loop | Serial | Serial | Exact Match |
| Strategy loop | Serial | Serial | Exact Match |
| Target choice | Dataset `sugg_idx` | Same | Exact Match |
| Rewrite | One per query/strategy | Same | Exact Match |
| Sampling | One answer call with five choices | Same | Exact Match |
| Evaluate timing | Answer cache updated before evaluation returns to caller | All five rows committed before evaluation starts | Equivalent; stronger durability |
| Persistence | JSON/pickle caches and output JSON | Relational rows plus CSV/JSON exports | Engineering Difference |
| Resume | Cache-based | Status-based; refuses legacy partial `n=5` batches | Engineering Difference |
| Random seed | No OpenAI API seed; ordinary local execution order | Local query shuffle seed 42 for staged subsets; no OpenAI API seed | Scientific Difference for staged subset selection; full sampling remains nondeterministic |
| Per-strategy mean | Mean across sampled responses/queries | Same conceptual aggregation | Equivalent |
| Variance | Exact downstream paper code not available in audited repository | Sample variance (`n-1`) plus 95% normal CI | Scientific provenance gap for displayed standard deviations |
| Outputs | Paper-specific cached JSON | Sample-level CSV, JSON, metric CSV, chart, claim validation | Engineering Difference |

The deterministic claim must be qualified. Database checkpointing and subset selection are deterministic; OpenAI completions are not, because neither implementation sends an API seed and historical backend state is unavailable.

## 3. Paper claim-to-code mapping

“Every claim” here means the paper's testable methodological and empirical GEO claims. Background statements, literature summaries, ethical discussion, and forecasts are not executable claims.

| Paper claim | Paper location | Current implementation | Status |
|---|---|---|---|
| GEO is a black-box content optimization framework | Sections 2–3 | Strategy rewrite → fixed-source answer generation → visibility evaluation | Fully implemented |
| GEO-bench contains 10,000 diverse queries and relevant web sources | Section 3; dataset card | Official HF artifact is used; only test split is run | Dataset provenance implemented; corpus-wide characterization not independently reproduced |
| Nine GEO methods are compared with No Optimization | Section 3.2; Table 1 | `STRATEGY_LABELS`, `GeoRewriter`, runner strategy loop | Fully implemented |
| Five sampled responses support each method/query evaluation | Experimental setup | Single `n=5` answer call and five persisted samples | Fully implemented |
| PAWC combines citation-associated words and position | Section 3.3 | `impression_wordpos_count_simple` port | Fully implemented |
| Word and Position metrics isolate PAWC factors | Section 3.3 | Separate normalized word and position functions | Fully implemented |
| Subjective Impression uses seven evaluator views | Section 3.3 / appendix | Seven pinned prompts and probability-weighted scores | Implemented with public-code/cache and calibration qualifications |
| GEO can improve visibility by up to 40% | Abstract; Section 4 | Full-run strategy metrics can test trend/magnitude | Method implemented; claim not reproduced until a complete run |
| Quotation, Statistics, and Cite Sources outperform baseline | Table 1; Section 4 | Explicit checks in `paper_conclusions.json` | Implemented, awaiting full-run evidence |
| Keyword Stuffing gives little benefit or harms visibility | Table 1; Section 4 | Explicit baseline comparison | Implemented, awaiting full-run evidence |
| Method effectiveness varies by domain/query type | Section 5.1; Table 3 | Tags are retained but no complete paper-equivalent tag analysis exists | Partially implemented |
| Lower-ranked/smaller sources receive larger relative gains, up to the reported large gains | Section 5.2; Table 2 | Target rank is retained; claim marked unsupported by current validator | Partially implemented |
| Combining methods can outperform single methods; Fluency + Statistics is strongest tested pair | Section 5.3; Figure 4 | Pairwise strategy campaign is not part of official runner | Intentionally omitted |
| Selected high-performing methods generalize to Perplexity | Section 6; Table 5 | No Perplexity paper-replication branch in this runner | Intentionally omitted |
| Quotation improves Perplexity PAWC and Statistics improves its subjective measure by the reported amounts | Section 6; Table 5 | No corresponding controlled run | Intentionally omitted |
| GEO-bench source/category diversity supports domain-level conclusions | Dataset/Section 3 | Metadata retained but full paper analysis suite absent | Partially implemented |
| The experiment uses fixed relevant responses without source summarization in the reported setup | Experimental setup | Stored full cleaned Top-5 passages supplied directly | Fully implemented for valid rows |
| Results are statistically summarized across stochastic responses | Experimental setup/results | Means, sample variance, CI, CSV/JSON | Implemented; exact historical deviation convention not verified |

The runner is therefore a replication of the paper's **main single-strategy GEO-bench experiment**, not a complete reproduction of every supplementary/domain/combination/in-the-wild experiment in the paper.

## 4. Complete register of remaining deviations

| Deviation | Reason | Intentional? | Affects fidelity? | Expected impact |
|---|---|---:|---:|---|
| Requested `gpt-3.5-turbo-16k` resolved to `gpt-3.5-turbo-0125` in measured runs | Historical alias/checkpoint no longer available as a frozen service | No | Yes, high | Different answer/rewrite distribution and citation patterns |
| No API seed in either implementation | Official code did not provide one; historic backend state unavailable | Yes, method-faithful | Yes, inherent | Exact outputs cannot be replayed |
| Subjective evaluator's historical model backend is not frozen | Legacy hosted model/versioning | No | Yes, medium/high | Judge score distribution can drift |
| Official subjective live code is unreachable after cache miss | Public repository contains early zero return and omits full private cache | No | Yes, provenance ambiguity | Platform reconstructs intended method; literal public execution differs |
| Subjective calibration not found in official executable code | Paper description exceeds released implementation | No | Yes, medium | Calibrated scale may differ; raw scores remain more directly auditable |
| Full-stage metadata says 997 but loader accepts 996 | One invalid query-text row plus three rows with fewer than five usable sources | No | Yes, medium | Full experiment population and cost/sample count differ |
| Dataset URL follows `main` | Loader was designed for convenient caching rather than immutable retrieval | No | Potentially | Future cache refresh could silently change inputs |
| Only test split is local | Runner targets paper test experiment | Yes | No for this scope | Training/validation analyses cannot be reproduced here |
| Direct fixed Top-5 loading differs from public `run_geo.py`'s incomplete visible source path | Public code/cache release is not self-contained | Yes | Low; improves paper alignment | Execution trace differs, controlled inputs match paper/dataset intent |
| Strategy prompt whitespace is not byte-identical for seven methods | Port normalized trailing/blank whitespace | No | Very low | Tokenization can differ at margins; semantic instruction unchanged |
| Objective tokenizer regex fallback | Resilience if NLTK assets are absent | Yes | Conditional, medium | Different sentence boundaries/word counts if activated |
| Metric ratios rounded to six decimals | Storage/reporting design | Yes | Very low | Last-digit aggregate differences |
| Staged query subsets are shuffled with seed 42 | Staged profiling/validation feature absent from paper | Yes | Yes for stages only | Stage 1/2/3 are not paper-defined samples; full set unaffected |
| Relational persist-before-evaluate and strict batch resume | Crash safety | Yes | No | Same generated choices, safer recovery |
| Sample variance and normal CI added | Research reporting enhancement | Yes | Potentially low/medium | Displayed spread may not match unpublished paper aggregation code |
| Concurrency absent | Deliberate fidelity policy | Yes | No | Execution order stays serial |
| Pairwise combinations, domain tables, rank tables, Perplexity study omitted | Runner scope is main single-strategy replication | Yes | Yes for whole-paper coverage | Cannot reproduce those paper claims |
| Additional diagnostics/metrics/exports | Platform provenance and operations | Yes | No | No change to paper metrics |

## 5. Fidelity scores

Scores express provenance confidence for the audited implementation, not empirical agreement with paper results. They are evidence-weighted audit judgments rather than statistically estimated probabilities.

| Dimension | Score | Basis |
|---|---:|---|
| Dataset Fidelity | **94/100** | Local test bytes match a verified official revision and Top-5 order/target are preserved; deduction for unpinned URL and 996/997 inconsistency |
| Prompt Fidelity | **98/100** | Answer prompt is byte-identical in sample comparison; strategy semantics match, with seven whitespace-only differences |
| Method Fidelity | **91/100** | Main single-strategy protocol, one rewrite, `n=5`, serial loops, and fixed sources match; staged sampling and incomplete ancillary studies deducted |
| Evaluation Fidelity | **84/100** | Objective formulas are direct ports and seven intended prompts/scoring match; calibration provenance, dead official path, fallback tokenizer, and rounding reduce confidence |
| Implementation Fidelity | **87/100** | Scientific operation is preserved despite DB persistence; public reference implementation itself is incomplete and post-paper |
| Model Fidelity | **52/100** | Requested names match, but current API routing does not reproduce the historical answer/rewrite checkpoint and judge backend cannot be frozen |
| **Overall Replication Fidelity** | **86/100** | High fidelity to the main published method, materially limited by historical model and a few disclosed provenance gaps |

## 6. Final scientific verdict

### **YES, WITH DISCLOSED MODERN MODEL DIFFERENCES**

A Princeton GEO author could reasonably agree that the platform implements the same published **main GEO-bench single-strategy methodology** because the decisive experimental structure is preserved: official dataset content, Top-5 order and `sugg_idx`, official transformations, byte-identical answer prompt construction, official generation parameters including one `n=5` call, one rewrite per strategy, and the published citation-based formulas.

That agreement should carry four explicit boundaries:

1. Results are a modern service replication, not exact recovery of the historical GPT-3.5 checkpoint.
2. The executable full population is currently 996 valid test queries, not the configured 997; reports must use the actual denominator.
3. Subjective results are a reconstruction of the intended public evaluator, with calibration provenance not fully recoverable from the released code.
4. Domain, source-rank, pairwise-combination, and Perplexity experiments are not reproduced by this runner, so the audit does not validate those paper claims empirically.

Absent those disclosures, an “exact replication” label would be too strong. With them, “scientifically faithful modern replication of the main Princeton GEO experiment” is justified.

## 7. Reproducibility record and code references

### Current platform

- [`official_replication_runner.py`](../backend/app/experiment/official_replication_runner.py): experiment construction, `n=5`, persist-before-evaluate, calibration, exports.
- [`geo_bench_loader.py`](../backend/app/experiment/geo_bench_loader.py): official dataset load, validation, Top-5 selection, `sugg_idx` mapping.
- [`geo_rewriter.py`](../backend/app/ge/geo_rewriter.py): official strategy prompts and rewrite cache.
- [`prompt_builder.py`](../backend/app/ge/prompt_builder.py): exact answer prompt/source formatting.
- [`chatgpt_provider.py`](../backend/app/providers/chatgpt_provider.py): concrete Chat Completions request and returned-model provenance.
- [`evaluator.py`](../backend/app/evaluation/evaluator.py): citation extraction, PAWC, Word, Position.
- [`subjective_evaluator.py`](../backend/app/evaluation/subjective_evaluator.py): seven official prompts, legacy completion request, logprob expectation, calibration helper.
- [`experiment_pipeline.py`](../backend/app/evaluation/experiment_pipeline.py): per-answer evaluation and descriptive statistics.
- [`paper_conclusions.json`](../backend/app/experiment/paper_conclusions.json): explicit main-paper claim checks and unsupported-scope declarations.

### Official sources

- [Paper abstract and revision history](https://arxiv.org/abs/2311.09735)
- [Paper HTML](https://arxiv.org/html/2311.09735)
- [Official repository](https://github.com/GEO-optim/GEO)
- [Pinned official repository tree](https://github.com/GEO-optim/GEO/tree/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888)
- [Official GEO-bench dataset](https://huggingface.co/datasets/GEO-Optim/geo-bench)
- [Audited GEO-bench revision](https://huggingface.co/datasets/GEO-Optim/geo-bench/tree/16a179f6bbb08ee7c357797ce8df483c5dd22130)

## 8. Audit limitations

- No paid API calls were made for this audit; observed model identifiers are taken from the existing measured profiler artifacts.
- No private author cache, unreleased source, paper-era OpenAI snapshot, or paper-era environment lockfile was available.
- Byte comparisons establish identity only for the files and sample-rendered prompts described above; they cannot establish equivalence of unavailable model weights or server-side sampling.
- This audit evaluates provenance and implementation coverage. It does not claim that the platform has reproduced the paper's numerical results until the full, correctly denominated experiment is run and reported.
