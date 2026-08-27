# Princeton GEO Method Fidelity Audit

Audit date: 2026-08-20  
Reference: Princeton GEO public repository commit [`c9e985f2`](https://github.com/GEO-optim/GEO/tree/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888)  
Scope: official replication runner only. No UI, concurrency, scheduling, or runtime optimization was changed.

## Classification rules

- **Exact Match** — the effective scientific input, sampling procedure, or formula is the same as the pinned public code.
- **Equivalent** — implementation form differs but the measured scientific quantity is unchanged.
- **Scientific Difference** — the difference can change generated answers, scores, or the experimental distribution.
- **Engineering Difference** — persistence, reporting, or orchestration differs without changing the scientific calculation.

## Executive result

Four correctable scientific differences existed in answer generation and are fixed:

1. `gpt-3.5-turbo` was replaced with the official `gpt-3.5-turbo-16k` identifier.
2. temperature `0.7` was replaced with the official `0.5`; `max_tokens=1024` is now explicit.
3. five independent requests were replaced with one Chat Completions request using `n=5`.
4. the answer prompt and `### Source N:` source formatting now match `src/generative_le.py` byte-for-byte.

The complete five-choice response is now committed before any objective or subjective evaluation begins. A crash during evaluation resumes from the stored choices and does not resample them.

No paid API request or live experiment was run during this audit.

## 1. Answer generation

Official path:

`src/run_geo.py::improve` → `src/utils.py::get_answer(..., num_completions=5, n=5)` → `src/generative_le.py::generate_answer` → `openai.ChatCompletion.create`

Current path after the fix:

`OfficialReplicationRunner.execute` → `OpenAILLMRunner.generate_many` → `ChatGPTProvider.generate_texts` → `client.chat.completions.create`

| Item | Official | Current after fix | Classification |
|---|---|---|---|
| Endpoint | Chat Completions | Chat Completions | Exact Match |
| Model identifier | `gpt-3.5-turbo-16k` | `gpt-3.5-turbo-16k` | Exact Match |
| Temperature | `0.5` | `0.5` | Exact Match |
| `max_tokens` | `1024` | `1024` | Exact Match |
| `top_p` | `1` | `1` | Exact Match |
| `n` | `5` | `5` | Exact Match |
| System message | none | none | Exact Match |
| User message | official prompt | official prompt, byte-for-byte regression tested | Exact Match |
| Source labels | `### Source 1:` … `### Source 5:` | identical | Exact Match |
| Presence/frequency penalties | omitted (API defaults) | omitted | Exact Match |
| Stop | omitted | omitted | Exact Match |
| Seed | omitted | omitted | Exact Match |
| Returned answer suffix | one newline appended | one newline appended | Exact Match |
| Choice ordering | API response order | sorted by API `choice.index` | Equivalent |

OpenAI documents that `n` is the number of choices generated for each prompt and that a response may contain multiple choices when `n > 1`: [Chat Completions API](https://developers.openai.com/api/reference/cli/resources/chat/subresources/completions), [stored Chat Completion response](https://developers.openai.com/api/reference/ruby/resources/chat/subresources/completions/methods/retrieve).

### Model availability limitation

The historical alias is retained because this task forbids evaluator/model substitution and prioritizes fidelity. OpenAI does not guarantee that a mutable historical alias reproduces the exact 2023 serving checkpoint, and the alias may be unavailable to a current account. Therefore the configured identifier is an **Exact Match**, but exact historical weights/backend state remain an unavoidable **Scientific Difference**. The runner now fails rather than silently falling back to another model.

## 2. GEO rewrite

Official path:

`src/run_geo.py::GEO_METHODS` → one strategy function in `src/geo_functions.py` → `call_gpt` → rewrite cache

Current path:

`OfficialReplicationRunner.execute` → `GeoRewriter.rewrite` → official prompt builder → rewrite cache → `OpenAILLMRunner.generate`

| Item | Result | Classification |
|---|---|---|
| Ten strategies and labels | Same baseline plus nine official transformations | Exact Match |
| Strategy prompt text | Pinned official prompt text | Exact Match |
| Rewrite model/temperature/top-p/max tokens | `gpt-3.5-turbo-16k`, `0`, `1`, `3192` | Exact Match |
| Rewrite frequency | Once per query/strategy source, before the five-answer batch | Exact Match |
| Rewrite cache key | User and system prompt content | Equivalent |
| Cached rewrite reuse | Reused across five samples and resumptions | Exact Match |
| Retry/storage implementation | Local implementation differs | Engineering Difference |

No rewrite code was changed.

## 3. Objective evaluation

The current `extract_citations_new`, `get_num_words`, `impression_wordpos_count_simple`, `impression_word_count_simple`, `impression_pos_count_simple`, and normalization logic are direct ports of `src/utils.py`.

| Item | Result | Classification |
|---|---|---|
| Citation extraction | Same bracketed-integer regular expression | Exact Match |
| Word contribution | Token length greater than two | Exact Match |
| Position decay | `exp(-index / (sentence_count - 1))` | Exact Match |
| Multi-citation division | Divide contribution by citations in the sentence | Exact Match |
| PAWC normalization | Divide by sum; uniform `1/n` when zero | Exact Match |
| Word and position scores | Official formulas | Exact Match |
| Selected source mapping | zero-based `sugg_idx` → one-based citation rank | Exact Match |
| Extra citation-count/first-position fields | Additional reporting only | Engineering Difference |
| Rounding stored selected metrics to six decimals | Below reported precision; aggregate conclusions unchanged | Equivalent |

No objective evaluation code was changed.

## 4. Subjective evaluation

| Item | Result | Classification |
|---|---|---|
| Seven dimensions | relevance, influence, uniqueness, diversity, follow-up, position, count | Exact Match |
| Prompts | Loaded from the seven files at pinned official commit | Exact Match |
| Evaluator identifier | `gpt-3.5-turbo-instruct` | Exact Match identifier; historical serving state unavailable |
| Calls | Seven independent Completion calls per answer | Exact Match |
| Parameters | temperature `0`, max tokens `3`, top-p `1`, zero penalties, `logprobs=5`, `n=1` | Exact Match |
| Probability weighting | normalized `exp(logprob)` expected score | Exact Match |
| Non-numeric token handling | official minimum score behavior | Exact Match |
| Dataset-level calibration | mean/variance matched to PAWC | Exact Match |

The current OpenAI account's availability/rate limits and the inability to freeze the historical evaluator checkpoint are unavoidable **Scientific Differences**. Per task constraints, the evaluator model was not replaced and no bridge model was activated.

## 5. Dataset and Top-5 sources

| Item | Result | Classification |
|---|---|---|
| Dataset | `GEO-Optim/geo-bench` test JSONL | Exact Match |
| Query ordering for a full run | Published file order after invalid-row filtering | Exact Match for retained rows |
| Top-5 ordering | First five stored sources, unchanged | Exact Match |
| Target selection | published `sugg_idx`, validated in `[0,4]` | Exact Match |
| Text field | published `cleaned_text`, falling back to `raw_text` | Exact Match to the current benchmark artifact |
| Missing/invalid rows | rows without five usable sources or valid `sugg_idx` are excluded | Engineering Difference required for executable fixed-input runs |
| Historical retrieval summaries | Not published as a complete frozen cache in the pinned repository | Scientific Difference, not repairable from available reference artifacts |

Important limitation: the pinned public `run_geo.py` can obtain summaries through its search/cache path, while the current reproducible runner deliberately uses the benchmark's frozen Top-5 passages. The pinned repository contains no complete historical cache from which the original summarized passages can be reconstructed. Switching to live retrieval would introduce time-varying inputs and would not recover the paper's historical inputs, so this audit does not make that change.

## 6. Reproducibility, checkpointing, and outputs

| Item | Result | Classification |
|---|---|---|
| API seed | Omitted in both implementations | Exact Match |
| Five-answer sampling | One request, one prompt, `n=5` | Exact Match |
| Strategy/query execution | Serial | Exact Match; no concurrency added |
| Stage subset selection | local `Random(42)` shuffle for staged protocols | Engineering Difference; stages are not part of the public runner |
| Full-run ordering | fixed dataset order | Exact Match |
| Rewrite cache | deterministic content key | Equivalent |
| Pre-evaluation checkpoint | all five answers committed atomically | Engineering Difference that preserves the official sample set |
| Resume after evaluation crash | evaluates stored answers without generation | Engineering Difference that preserves scientific outputs |
| Legacy partial five-request groups | rejected, not mixed with official batches | Scientific safeguard |
| CSV/JSON exports | stable sample indices and stored raw prompt/response | Engineering Difference |

The official API call has no numeric `seed`; therefore stochastic bit-for-bit reproduction across requests is not promised. Determinism here means that once the five choices are returned, checkpoint/resume and exports do not alter or resample them.

## Implemented scientific fixes

- Official answer constants and one `n=5` request in `official_replication_runner.py`.
- Multi-choice transport in `llm_runner.py` and `chatgpt_provider.py` without concurrency.
- Exact official answer prompt and source formatting in `prompt_builder.py`.
- Atomic five-answer staging and post-commit evaluation in `experiment_repository.py`.
- Explicit rejection of pre-fidelity experiment configurations and legacy partial groups.

## Regression evidence

`python3 -m unittest tests.test_experiment_research_core -v` passes 12 tests.

The one-query regression uses five fixed answers and verifies:

1. the legacy per-answer evaluation and new batched-answer evaluation produce identical `EvaluationResult` values for all five answers;
2. the provider emits exactly one request with model `gpt-3.5-turbo-16k`, temperature `0.5`, `max_tokens=1024`, top-p `1`, and `n=5`;
3. no seed, stop sequence, or penalty override is sent;
4. all five answers are persisted before the first evaluation event;
5. all five staged samples transition to completed state.

This is a deterministic, no-API regression. A live “before/after” generation cannot validly demand identical text because the official method intentionally samples stochastically and supplies no seed. Scientific equivalence is therefore demonstrated by holding the five sampled answers constant and proving that batching, persistence, and evaluation preserve the same outputs and metrics.

## Remaining scientific differences

1. The exact historical `gpt-3.5-turbo-16k` and `gpt-3.5-turbo-instruct` serving checkpoints cannot be frozen through current aliases.
2. The complete historical search-summary cache used during the paper run is not published in the pinned repository; frozen current GEO-bench Top-5 passages are the closest reproducible input artifact.
3. OpenAI sampling without an explicit seed is not bit-for-bit reproducible across separate executions. This is inherited from the official method.

No other correctable scientific difference was found in the audited runner.
