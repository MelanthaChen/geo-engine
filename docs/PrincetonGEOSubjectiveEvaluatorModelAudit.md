# Princeton GEO Subjective Evaluator Model Audit

**Date:** 2026-08-20  
**Scope:** Research recommendation only. No experiment logic or application code was changed, and no paid API calls were made.

## Executive recommendation

`gpt-3.5-turbo-instruct` is now explicitly marked **Deprecated** by OpenAI and is available only through the legacy Completions endpoint. OpenAI does not publish a model-specific migration statement for the instruct variant, but its GPT-3.5 guidance recommends `gpt-4o-mini` in place of GPT-3.5 Turbo because it is cheaper, more capable, and similarly fast.

For a contemporary continuation of the Princeton GEO experiment, the best practical replacement is the pinned snapshot **`gpt-4o-mini-2024-07-18`**, using Chat Completions with temperature 0 and top-token log probabilities. It is a small, non-reasoning model suited to focused classification/scoring tasks and supports a stable snapshot.

This substitution is **scientifically defensible only as a documented evaluator migration or contemporary replication**, not as an exact reproduction of the original subjective metric. Changing the evaluator changes the measurement instrument: its tokenizer, instruction tuning, probability distribution, and chat framing differ from `gpt-3.5-turbo-instruct`. Keeping the seven prompts and probability-weighted scoring formula unchanged preserves the construct and aggregation procedure, but does not establish measurement equivalence.

Before a staged run, perform a preregistered bridge validation on a fixed, representative sample and report both evaluator versions where cached legacy scores exist. Do not mix legacy and replacement-model scores inside one aggregate.

## 1. Official Princeton implementation

The audit pins the official repository at commit [`c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888`](https://github.com/GEO-optim/GEO/tree/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888).

The intended live path in [`src/utils.py`, lines 140–215](https://github.com/GEO-optim/GEO/blob/c9e985f2bc4b539a01e8e9d226ff2a3d8d29a888/src/utils.py#L140-L215) loops over the files in `geval_prompts/*.txt` and makes one request per prompt:

```python
for prompt_file in glob('geval_prompts/*.txt'):
    _response = openai.Completion.create(
        model='gpt-3.5-turbo-instruct',
        prompt=cur_prompt,
        temperature=0.0,
        max_tokens=3,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        logprobs=5,
        n=1
    )
    logprobs = _response['choices'][0]['logprobs']['top_logprobs'][0]
    total_sum = sum(math.e ** v for v in logprobs.values())
    avg_score = sum(
        convert_to_number(k) * (math.e ** v) / total_sum
        for k, v in logprobs.items()
    )
```

The seven dimensions are relevance, influence, uniqueness, diversity, follow-up, subjective position, and subjective count. The score is the expected bounded 1–5 value under the first generated token's returned top-five token probabilities.

Important reproducibility limitation: in the public commit, a cache-miss `return` appears before the live request block, making that live block unreachable in the checked-in execution path. The code nevertheless documents the authors' intended request and scoring procedure. Exact historical outputs depend on the authors' cache and the historical service-side model state.

## 2. Current platform implementation

The platform implementation in [`backend/app/evaluation/subjective_evaluator.py`](../backend/app/evaluation/subjective_evaluator.py) is an explicit port of that intended live block:

- seven independent calls per generated answer;
- the seven official prompt files pinned to the official commit;
- `gpt-3.5-turbo-instruct` through legacy Completions;
- temperature 0, `max_tokens=3`, `top_p=1`, zero penalties, `logprobs=5`, and `n=1`;
- the same bounded numeric conversion and normalized probability-weighted expectation;
- the same downstream per-facet calibration against PAWC.

The profiler observed the actual returned model identifier `gpt-3.5-turbo-instruct:20230824-v2`, with 502.4 average prompt tokens, 1.0 completion token, 503.4 total tokens, and 0.59 seconds average latency across 1,050 evaluator calls.

## 3. Model status and official replacement

### Status

OpenAI's [`gpt-3.5-turbo-instruct` model page](https://developers.openai.com/api/docs/models/gpt-3.5-turbo-instruct) labels the model **Deprecated**, describes it as an older GPT-3-era-capability model, and states that it works only with legacy Completions. The page still lists availability and rate limits; therefore “deprecated” should not be reported as “already shut down.” OpenAI currently gives no retirement date on that model page.

The reported RPD failure is an account/model rate-limit constraint, not proof that the endpoint has been retired. Published limits vary by usage tier and actual project limits must be read from the account's limits page or response headers.

### Recommended replacement

OpenAI's [`GPT-3.5 Turbo` guidance](https://developers.openai.com/api/docs/models/gpt-3.5-turbo) says to use `gpt-4o-mini` in place of GPT-3.5 Turbo. The [`GPT-4o mini` model page](https://developers.openai.com/api/docs/models/gpt-4o-mini) describes it as a fast, affordable small model for focused tasks and exposes the stable snapshot `gpt-4o-mini-2024-07-18`.

`gpt-4o-mini-2024-07-18` is the closest supported practical choice because:

1. OpenAI explicitly positions GPT-4o mini as the GPT-3.5 replacement.
2. It is a small, fast, non-reasoning instruction-following model, closer to the evaluator's classification role than a reasoning model.
3. Chat Completions exposes per-token `logprob` and `top_logprobs`, so the existing probability-weighted 1–5 calculation can be retained.
4. A dated snapshot avoids alias drift during one experiment.

It is not a drop-in endpoint replacement. `gpt-4o-mini` does not support legacy Completions, so the same prompt must be represented as a Chat Completions message. That framing difference is itself part of the evaluator migration and must be documented.

## 4. Scientific defensibility

### What remains identical

- the construct definitions in all seven official prompts;
- the query, answer, and selected-source-rank inputs;
- one evaluation per facet per answer;
- deterministic sampling configuration (`temperature=0`);
- probability-weighted conversion of first-token alternatives to a 1–5 score;
- per-facet storage, PAWC calibration, and final aggregation.

### What changes

- model weights and instruction tuning;
- tokenizer and candidate first-token set;
- calibration/confidence of returned token probabilities;
- legacy plain-prompt framing versus chat-message framing;
- model knowledge and safety behavior;
- potentially the ordering and variance of strategy scores.

Temperature 0 does not remove these differences. The metric uses the entire returned top-token probability distribution, not only the selected token, so even identical visible answers can yield different expected scores.

### Methodological conclusion

The replacement is defensible for a **construct-preserving contemporary replication**, provided the model migration is declared as a deviation and validated. It is not defensible to label resulting subjective scores as an exact reproduction of the original evaluator.

Recommended bridge protocol before Stage 1:

1. Freeze `gpt-4o-mini-2024-07-18`; never use the floating alias for the reported run.
2. Select a fixed stratified sample spanning strategies, query categories, source ranks, and score ranges.
3. Where official/legacy cached facet scores exist, score the exact same answers with the replacement model.
4. For each facet and the final calibrated metric, report Pearson and Spearman correlation, mean shift, variance ratio, rank-order agreement, and strategy-level effect-direction agreement.
5. Predeclare acceptance thresholds before examining results. A reasonable starting policy is Spearman correlation at least 0.80 and no reversal of the paper's primary strategy conclusions, but this threshold is a research-policy choice, not an OpenAI or Princeton standard.
6. If bridge criteria fail, report objective PAWC as the faithful primary result and treat replacement-model subjective scores as a separate contemporary sensitivity analysis.
7. Never combine scores from the two evaluator models in one calibrated population.

## 5. Cost estimate

The estimate reuses the platform's measured evaluator workload rather than assumed call sizes. It changes only token prices and assumes approximately the same prompt token count; Chat Completions will add a small message-framing overhead, so actual cost should be reprofiled before budgeting.

Current OpenAI prices per one million tokens are:

| Model | Input | Output |
|---|---:|---:|
| `gpt-3.5-turbo-instruct` | $1.50 | $2.00 |
| `gpt-4o-mini` | $0.15 | $0.60 |

Using measured token volumes:

| Scope | Evaluator calls | Prompt tokens | Completion tokens | Legacy evaluator | GPT-4o mini projection | Difference |
|---|---:|---:|---:|---:|---:|---:|
| Stage 1, 30 queries | 10,500 | 5,275,660 | 10,500 | $7.93 | **$0.80** | -$7.14 / -89.95% |
| Full, 997 valid queries | 348,950 | 175,327,767 | 348,950 | $263.69 | **$26.51** | -$237.18 / -89.95% |

If all other pipeline stages remain at their profiled costs, the approximate total becomes **$5.20 for Stage 1** instead of $12.34, and **$172.83 for the full benchmark** instead of $410.01. These are projections, not measured replacement-model totals.

## 6. Runtime and rate-limit estimate

The existing profiler measured 0.59 seconds per legacy evaluator call. At unchanged sequential latency:

| Scope | Sequential evaluator time |
|---|---:|
| Stage 1 | about 1.72 hours |
| Full benchmark | about 57.2 hours |

OpenAI publishes GPT-4o mini as similarly fast to GPT-3.5, but does not guarantee an exact latency ratio. Consequently, no evidence-backed runtime reduction can be claimed before a small, unpaid-or-minimal bridge profile measures the new endpoint. Chat overhead is negligible relative to hundreds of prompt tokens, but service latency and queueing dominate wall time.

Published GPT-4o mini Tier 1 limits are 500 RPM, 10,000 RPD, and 200,000 TPM. Under those limits:

- Stage 1's 10,500 evaluator calls cannot finish in one calendar-day quota; it requires at least two quota days even though the throughput bounds are only about 21 minutes by RPM and 26.4 minutes by TPM.
- The full evaluator workload requires at least 35 quota days by RPD at Tier 1.
- At Tier 2, the model page lists 5,000 RPM and 2,000,000 TPM with no published RPD value; the token-throughput lower bound for the full evaluator is about 87.8 minutes, but sequential execution would still be dominated by per-request latency.

Therefore replacing the model removes the legacy-model dependency and cuts projected evaluator cost sharply, but it does **not automatically solve Stage 1 throughput for a Tier 1 project**. The actual project tier and headers must be verified before scheduling.

## Final answers

1. **Is `gpt-3.5-turbo-instruct` deprecated or legacy?** Yes. OpenAI marks the model Deprecated and restricts it to legacy Completions. It is still listed, with no retirement date stated on the model page.
2. **Officially recommended replacement?** OpenAI recommends GPT-4o mini for GPT-3.5 workloads. There is no separate official promise that it reproduces `gpt-3.5-turbo-instruct` log-probability behavior.
3. **Best current model for this evaluator?** `gpt-4o-mini-2024-07-18`, because it is the official GPT-3.5 replacement, is small/non-reasoning, supports token log probabilities through Chat Completions, and can be snapshot-pinned.
4. **Scientifically defensible?** Yes as a disclosed, validated contemporary replication; no as an exact reproduction without bridge evidence.
5. **Cost/runtime impact?** Evaluator cost projects from $7.93 to about $0.80 for Stage 1 and from $263.69 to about $26.51 for the full benchmark. Runtime cannot be credibly claimed to improve until measured; at current sequential latency it remains about 1.72 and 57.2 evaluator-hours, respectively, and Tier 1 RPD remains a blocking constraint.

