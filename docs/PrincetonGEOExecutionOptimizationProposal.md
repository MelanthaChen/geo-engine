# Princeton GEO Execution Optimization Proposal

**Date:** 2026-08-20  
**Scope:** Source-level execution audit only. No runner, provider, persistence, experiment, or evaluation code was changed. No API calls were made.

## Executive recommendation

The current runner is fully serial at four nested levels:

```text
query
  → strategy rewrite
    → answer sample × 5
      → subjective facet × 7
        → persist completed sample
```

The official Princeton implementation is also serial across queries and strategies, but it generates the five answers for one prompt in a single Chat Completions request using `n=5`. The safest optimization sequence is:

1. Adopt one `n=5` answer request per query/strategy only after making the five returned choices a durable, atomic batch.
2. Execute the seven subjective facets concurrently behind a model-specific bounded semaphore.
3. Introduce one global deterministic work scheduler for independent query/strategy units, with worker-owned database sessions and centralized provider rate limiters.
4. Keep calibration, aggregate statistics, and final completion marking behind a full-run barrier.

Do not implement nested unbounded concurrency. Strategy and query concurrency draw from the same API quotas; one global scheduler plus per-model limits is simpler, safer, and just as fast.

Using the existing three-query latency profile, `n=5` plus seven-way facet concurrency projects the sequential Stage 1 runtime from **3.34 hours to approximately 0.97–1.19 hours** before strategy/query worker parallelism, a **64–71% reduction**. A bounded three-worker scheduler could theoretically reduce the compute-bound portion to roughly **19–24 minutes**, but real wall time may be dominated by RPM, TPM, RPD, retries, and database contention. This range must be validated with a small timing-only pilot.

## Evidence and current execution graph

### Official implementation

At pinned official commit [`c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888`](https://github.com/GEO-optim/GEO/tree/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888):

- [`src/run_geo.py`, lines 63 and 85](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/run_geo.py#L63-L85) calls `get_answer(..., num_completions=5, n=5)` for the baseline and every strategy.
- [`src/generative_le.py`, lines 17–46](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/generative_le.py#L17-L46) sends one Chat Completions request with `n=num_completions` and returns all response choices.
- [`src/run_geo.py`, lines 82–95](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/run_geo.py#L82-L95) executes strategies sequentially.
- The public code contains no query-, strategy-, or evaluator-level executor or worker pool.
- [`src/utils.py`, lines 181–208](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/utils.py#L181-L208) documents seven independent subjective prompt calls in a loop. The public cache-miss return immediately above makes this live block unreachable in that commit, but it still documents the intended evaluator call structure.

OpenAI's [Chat Completions API reference](https://developers.openai.com/api/reference/cli/resources/chat/subresources/completions/methods/create) defines `n` as the number of choices generated for each input and states that output-token charging covers all generated choices. It also describes `seed` as best-effort rather than guaranteed deterministic behavior.

### Current platform

[`OfficialReplicationRunner.execute`](../backend/app/experiment/official_replication_runner.py) performs:

```text
for query in selected_entries:                         serial
  ensure query/documents
  for strategy in ten strategies:                     serial
    find missing sample indexes
    rewrite once for that strategy                     0 or 1 API request
    for missing sample_index in 0..4:                  serial
      generate one answer                              1 API request, n=1
      objective evaluation                             local
      for each of seven subjective facets:             serial
        evaluate facet                                 1 API request
      store one completed run/evaluation/result         one transaction
  update query progress
calibrate all subjective vectors                        full-run barrier
mark completed and aggregate statistics                 full-run barrier
```

The current measured averages are:

| Operation | Average latency | Stage 1 calls | Stage 1 sequential time |
|---|---:|---:|---:|
| Answer generation | 2.736 s | 1,500 | 68.4 min |
| Strategy rewrite | 6.582 s | 270 | 29.6 min |
| Subjective facet | 0.586 s | 10,500 | 102.6 min |
| **Total provider time** |  | **12,270** | **3.34 h** |

Local parsing, PAWC, descriptive statistics, calibration, and database work are not the dominant runtime.

## Existing methodology differences that are not runtime optimizations

The pinned official `generate_answer` defaults to `gpt-3.5-turbo-16k`, temperature `0.5`, and `max_tokens=1024`. The current runner records `gpt-3.5-turbo`, sends temperature `0.7`, and leaves the answer max-token limit unset. These are pre-existing fidelity questions. This proposal does **not** recommend changing them because doing so would combine a methodological change with an execution optimization.

Likewise, neither implementation passes an API `seed` for answer generation. The current experiment's seed 42 controls dataset shuffling, and `query_index` is stored as provenance, but neither value seeds OpenAI sampling. Parallel scheduling can preserve the exact dataset order, stored seed values, prompts, and choice-to-sample mapping; it cannot guarantee byte-identical stochastic model outputs across reruns. OpenAI documents API seed determinism only as best effort.

## A. Answer generation with `n=5`

### Methodological assessment

**Recommendation: yes, with a durable batch boundary.** One request returning five choices is the official implementation and preserves the intended five-answer sampling design more faithfully than five requests returning one choice each.

What can be preserved exactly:

- identical system/user messages;
- identical model, temperature, top-p, maximum-output configuration, and penalties;
- five answers per strategy;
- canonical `response.choices[index] → sample_index=index` mapping;
- identical downstream evaluation of each individual answer;
- identical final run/evaluation/metric/result rows.

What cannot be proven:

- OpenAI does not document that `n=5` has the same joint statistical distribution as five separately submitted requests.
- Neither path has guaranteed reproducibility without a deterministic model snapshot and guaranteed seed semantics.
- Switching request shape will not reproduce already-generated sample text exactly.

For a fresh official replication, `n=5` is nevertheless the stronger fidelity choice because it matches the published source procedure.

### Exact request and token impact

| Scope | Current answer requests | Proposed answer requests | Reduction |
|---|---:|---:|---:|
| Per query | 50 | 10 | 80% |
| Stage 1, 30 queries | 1,500 | 300 | 80% |
| Full, 997 queries | 49,850 | 9,970 | 80% |

Completion-token volume should remain approximately unchanged because five answers are still generated. Prompt input is expected to be counted once per `n=5` request rather than once for each of five requests; this must be verified from actual response usage in the timing pilot.

| Scope | Current answer prompt tokens | Projected `n=5` prompt tokens | Completion tokens | Total-token reduction |
|---|---:|---:|---:|---:|
| Stage 1 | 6,815,850 | ~1,363,170 | ~329,340 unchanged | ~76.3% for answer generation |
| Full | 226,513,415 | ~45,302,683 | ~10,945,066 unchanged | ~76.3% for answer generation |

Across the entire pipeline, this projects Stage 1 tokens from 12,960,780 to approximately 7,508,100 and full-run tokens from 430,729,922 to approximately 249,519,190, a roughly **42.1% total-token reduction**. These are projections until a real `n=5` usage record confirms input accounting.

### Runtime estimate

Let `L5` be measured latency for one five-choice request. Then:

- Stage 1 answer time = `300 × L5`.
- Full answer time = `9,970 × L5`.

If `L5` is one to two times the measured single-choice latency, Stage 1 answer time becomes approximately **13.7–27.4 minutes**, versus 68.4 minutes today. Total Stage 1 becomes approximately **2.43–2.66 hours** before any other optimization, a **20–27% overall reduction**.

This latency ratio is an estimate, not an API guarantee. A 3–5 prompt pilot should measure `L5` before changing the planner.

### Resume and recovery requirement

Current recovery is sample-granular: each answer is evaluated and committed before generating the next answer. A naive `n=5` implementation would create a failure window: if choices 0–2 are committed and the process dies, generating `n=2` later does not reconstruct choices 3–4 from the original provider response.

Required design:

1. Persist the provider request identity, actual model/system fingerprint, all five raw choices, usage, and canonical indexes immediately after the API returns.
2. Only then evaluate and upsert each choice independently.
3. Resume evaluation from that durable batch without calling the model again.
4. Treat existing partially completed strategy groups as legacy groups: finish them with the old single-sample path or restart them as a separately identified fresh batch. Do not silently mix a new `n=5` response with prior samples.

Final experiment persistence remains unchanged; the durable batch is recovery metadata.

## B. Concurrent strategies

### Dependency analysis

Different strategies for the same query share only immutable inputs: query, official Top-5 documents, selected target rank, and experiment configuration. Each strategy has its own rewrite, final prompt, five answers, evaluations, and persisted sample keys. There is no mathematical dependency between strategy scores before final aggregation.

**Conclusion: strategies may execute concurrently without changing the methodology**, provided output ordering and persistence identity remain canonical.

### Safety prerequisites

- Pre-create the `ExperimentQuery` and its five document rows before dispatching strategies.
- Give every worker its own SQLAlchemy session; the current shared session is not thread-safe.
- Add or enforce idempotency for `(experiment_id, experiment_query_id, strategy, sample_index)` so retries cannot create duplicate completed runs.
- Collect outputs by the configured strategy order, never by completion order.
- Do not update `current_strategy` as a scientific value; it is operational progress only.
- Keep dataset-level calibration and statistics behind the all-work-complete barrier.

### Rewrite-cache hazard

The current JSON rewrite cache performs an unlocked read-modify-write. Concurrent cache misses can overwrite one another or corrupt the file. Safe options, in preference order:

1. Precompute/cache the nine rewrites for a query before dispatching answer/evaluation tasks.
2. Move cache writes behind a single writer or an atomic file lock.
3. Store rewrites in a database table keyed by prompt checksum.

The rewritten text must be immutable once selected for a strategy batch. Two workers must never independently generate competing rewrites for the same key.

### Impact

| Dimension | Impact |
|---|---|
| API requests | No change |
| Token usage | No change absent extra retries |
| Runtime | Ideally approaches division by worker count until RPM/TPM limits dominate |
| Reproducibility | Dataset/strategy/sample mapping unchanged; model text is not guaranteed identical because API calls are stochastic |
| Recovery | Improves if work units are leased/idempotent; degrades badly without unique keys and worker-owned sessions |

With the proposed batched-answer and concurrent-facet path taking roughly 0.97–1.19 Stage 1 hours serially, three fully utilized strategy workers give an ideal lower estimate of **19–24 minutes**. This is an optimistic compute-bound bound, not a quota-aware forecast.

## C. Concurrent queries

Different benchmark queries are scientifically independent until population calibration and aggregate statistics. They can execute concurrently with the same safeguards as strategies.

The experiment seed behavior can remain identical:

- perform `Random(42).shuffle(entries)` once during experiment creation, as today;
- persist the selected entry list and its canonical query indexes before dispatch;
- retain each existing `seed_value=query_index`;
- calculate progress from completed query groups, not from the largest finished index.

### Recommended architecture

Do not create a query pool containing strategy pools containing facet pools. Flatten independent work into deterministic units and control concurrency globally:

```text
deterministic work manifest
  key = (query_index, strategy_index)

global scheduler
  ├─ rewrite/answer semaphore for GPT-3.5 chat model
  ├─ subjective semaphore for evaluator model
  └─ single-writer or worker-owned transactional persistence
```

Query concurrency is useful when one query is waiting on retries or long completions, but once a global strategy queue saturates both provider semaphores, additional query nesting provides no throughput benefit.

| Dimension | Impact |
|---|---|
| API requests | No change |
| Token usage | No change absent retries |
| Runtime | Hides per-query tail latency; bounded by global provider and database capacity |
| Reproducibility | Canonical manifest preserves selection/order/provenance; stochastic API outputs remain non-bit-reproducible |
| Recovery | Requires task leases/idempotency and progress derived from persisted completion counts |

## D. Concurrent subjective evaluation

Each of the seven subjective dimensions receives the same immutable `(query, answer, selected_rank)` with a different official prompt. Each result is converted independently from its first-token top-five log probabilities. The seven values are averaged only after all calls complete.

**Conclusion: the seven calls can execute concurrently without changing the scoring algorithm.** Collect results into keys from the canonical `OFFICIAL_PROMPT_FILES` order; never rely on future completion order.

### Exact impact

| Dimension | Impact |
|---|---|
| API requests | Unchanged: 7 per answer |
| Token usage | Unchanged |
| Scoring | Unchanged when each response is paired with its facet key |
| Ideal latency | Per answer changes from sum of 7 calls to maximum of 7 calls |
| Stage 1 subjective time | 102.6 min → ideal 14.7 min |
| Full subjective time | 56.8 h → ideal 8.1 h |

With only this change, measured provider time projects from 3.34 to approximately **1.88 Stage 1 hours**, a **44% reduction**. Allowing for throttling and tail latency, budget **15–25 minutes** for Stage 1 subjective work rather than the ideal 14.7 minutes.

### Recovery

If final persistence must remain exactly sample-atomic, wait for all seven calls and persist the completed sample exactly as today. A failed facet may cause successful sibling calls to be repeated on resume. To avoid paid duplicate work without changing final experiment rows, store facet-call recovery records in a sidecar/checkpoint keyed by `(run batch, sample_index, facet, evaluator model, prompt checksum)`, then assemble the existing evaluation record only when all seven are present.

## Other safe optimizations

### Separate generation from evaluation

Once a five-choice answer batch is durably stored, objective and subjective evaluation can proceed independently of later generation. This pipelines slow evaluator work behind subsequent strategy generation without changing any metric.

### Preload official prompts

Load and checksum all seven pinned prompt files before starting workers. The existing process-local LRU cache is safe after warm-up, but concurrent first loads create unnecessary network requests and another failure source.

### Retain local evaluation as synchronous work

Citation parsing, PAWC, word score, and position score are fast and deterministic. Threading them individually adds complexity without material benefit. Run them in the worker that owns the sample.

### Do not use OpenAI Batch API for runtime acceleration

The asynchronous Batch API may improve cost and quota treatment, but it is not a low-latency mechanism and changes recovery/operational timing substantially. It is not recommended for this runtime-focused change.

## Combined projections

These estimates use the measured profile and assume `n=5` latency is one to two times a single-choice request.

| Configuration | Stage 1 provider time | Full provider time | Stage 1 reduction | Request change | Token change |
|---|---:|---:|---:|---:|---:|
| Current serial | 3.34 h | 111.12 h | — | — | — |
| `n=5` answers only | 2.43–2.66 h | 80.8–88.4 h | 20–27% | -1,200 Stage 1 / -39,880 full | ~-42.1% total |
| Seven-way subjective only | 1.88 h ideal | 62.4 h ideal | 44% | none | none |
| `n=5` + seven-way subjective | **0.97–1.19 h** | **32.1–39.7 h** | **64–71%** | as above | ~-42.1% total |
| Prior row + 3 global workers | **19–24 min ideal** | **10.7–13.2 h ideal** | **88–90% ideal** | as above | ~-42.1% total |

The worker estimates are lower bounds. Actual project limits may dominate. In particular, Stage 1 with the legacy subjective evaluator still requires 10,500 subjective requests; an RPD limit below that cannot be overcome with concurrency.

## Reproducibility and persistence contract

An implementation should be rejected unless it proves all of the following:

1. The persisted benchmark entry list and query indexes are byte-identical before and after optimization.
2. Every strategy uses the same rewrite text for all five choices.
3. One answer batch has exactly five uniquely indexed choices.
4. Every choice receives the same objective evaluator and exactly seven named subjective facets.
5. Final calibration uses the same complete aligned population and occurs only after all samples finish.
6. Final database cardinality, evaluator versions, metric names, prompts, answers, and strategy/sample identities match the existing schema contract.
7. Restarting at every injected failure point produces neither duplicate rows nor missing facets and does not regenerate a successfully persisted provider batch.
8. Dataset seed 42, entry ordering, query `seed_value`, and strategy ordering remain unchanged.
9. Provider concurrency is bounded independently by model, with retry jitter and server-provided rate-limit guidance.
10. A pre/post dry integration test compares deterministic fake-provider outputs exactly, then a minimal real timing pilot measures only latency and usage—not scientific outcomes.

## Proposed rollout sequence

### Phase 0 — measurement harness

- Add no execution changes.
- Record per-operation queue time, request time, retry count, rate-limit headers, and database time.
- Build a deterministic fake provider returning five indexed choices and seven facet responses.

### Phase 1 — `n=5` with durable batches

- Implement the batch persistence boundary.
- Preserve canonical choice indexes and legacy-partial-group handling.
- Run failure-injection and resume tests.
- Measure prompt-token accounting and `L5` on 3–5 prompts.

### Phase 2 — concurrent subjective facets

- Start with a global evaluator concurrency of 3, then 7 if rate limits permit.
- Keep sample completion atomic and add facet checkpoints only if duplicate-call cost matters.

### Phase 3 — global query/strategy scheduler

- Pre-create the work manifest.
- Use worker-owned sessions, idempotent keys, and concurrency-safe rewrite caching.
- Start at three workers and tune from observed TPM/RPM headroom.

### Phase 4 — validation gate

- Run an identical fake-provider experiment through serial and optimized executors and require byte-equivalent persisted scientific fields.
- Run a small real-provider timing pilot and compare only request counts, token usage, latency, cardinality, and recovery behavior.
- Do not compare exact generated text as a concurrency invariant because the current API path is unseeded and stochastic.

## Final decisions

| Area | Safe to optimize? | Recommendation |
|---|:---:|---|
| Answer generation | Yes, conditionally | Use official `n=5`; first persist the complete response batch atomically. |
| Strategy execution | Yes | Use a bounded global work queue; fix cache and database concurrency hazards first. |
| Query execution | Yes | Dispatch from a precomputed canonical manifest; do not nest unbounded pools. |
| Seven subjective facets | Yes | Run concurrently and collect by facet key; keep final sample persistence atomic. |
| Calibration/statistics | No parallel need | Preserve as a full-run barrier exactly as implemented. |

The highest-confidence near-term change is **`n=5` plus concurrent subjective facets**. It matches the official five-choice request structure, removes repeated prompt processing, preserves evaluator mathematics, and offers a projected 64–71% runtime reduction without requiring broad query-level concurrency. Strategy/query parallelism should follow only after idempotency, session ownership, progress accounting, and rewrite-cache safety are in place.

