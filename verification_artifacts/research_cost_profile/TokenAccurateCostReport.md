# Princeton GEO Token-Accurate Cost Profile

Profile sample: 3 official GEO-bench queries using the unchanged full pipeline.

Measured profiling cost: **$0.9339**.

## Actual model and call graph

`OfficialReplicationRunner` → `GeoRewriter` → Chat Completions (strategy rewrite); `OfficialReplicationRunner` → one Chat Completions request with `n=5` per strategy (five answers are committed before evaluation); `ExperimentEvaluationPipeline` → seven legacy Completions calls (Subjective Impression). PAWC, Word, Position, calibration, statistics, trend verification, export and charting are local and make no provider calls.

There is no model fallback. Context-length failures retry the same rewrite model after prompt truncation; every retry is independently metered.

**Model identity finding:** the table below reports the actual model identifiers returned by the API for this profiling run. Costs use those returned identifiers when pricing is configured.

## Measured averages

| Pipeline stage | Actual calls | Actual model(s) | Avg prompt tokens | Avg completion tokens | Avg total tokens | Avg latency | Avg cost/call |
|---|---:|---|---:|---:|---:|---:|---:|
| answer_generation | 30 | gpt-3.5-turbo-0125 | 4484.3 | 1031.6 | 5515.9 | 4.15s | $0.003790 |
| strategy_rewrite | 27 | gpt-3.5-turbo-0125 | 1086.4 | 794.3 | 1880.7 | 6.89s | $0.001735 |
| subjective_evaluation | 1050 | gpt-3.5-turbo-instruct:20230824-v2 | 489.7 | 1.0 | 490.7 | 0.86s | $0.000737 |

## Projected budgets

| Stage | Purpose | Calls | Prompt tokens | Completion tokens | Total tokens | Runtime | Projected cost | % of stage cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| stage1 | answer_generation | 300 | 1,345,290 | 309,480 | 1,654,770 | 0.35h | $1.14 | 12.2% |
| stage1 | strategy_rewrite | 270 | 293,330 | 214,470 | 507,800 | 0.52h | $0.47 | 5.0% |
| stage1 | subjective_evaluation | 10,500 | 5,141,940 | 10,520 | 5,152,460 | 2.52h | $7.73 | 82.8% |
| stage2 | answer_generation | 1,000 | 4,484,300 | 1,031,600 | 5,515,900 | 1.15h | $3.79 | 12.2% |
| stage2 | strategy_rewrite | 900 | 977,767 | 714,900 | 1,692,667 | 1.72h | $1.56 | 5.0% |
| stage2 | subjective_evaluation | 35,000 | 17,139,800 | 35,067 | 17,174,867 | 8.40h | $25.78 | 82.8% |
| stage3 | answer_generation | 3,000 | 13,452,900 | 3,094,800 | 16,547,700 | 3.46h | $11.37 | 12.2% |
| stage3 | strategy_rewrite | 2,700 | 2,933,300 | 2,144,700 | 5,078,000 | 5.16h | $4.68 | 5.0% |
| stage3 | subjective_evaluation | 105,000 | 51,419,400 | 105,200 | 51,524,600 | 25.21h | $77.34 | 82.8% |
| full | answer_generation | 9,970 | 44,708,471 | 10,285,052 | 54,993,523 | 11.50h | $37.78 | 12.2% |
| full | strategy_rewrite | 8,973 | 9,748,334 | 7,127,553 | 16,875,887 | 17.16h | $15.57 | 5.0% |
| full | subjective_evaluation | 348,950 | 170,883,806 | 349,615 | 171,233,421 | 83.79h | $257.02 | 82.8% |

## Stage totals

| Stage | Calls | Prompt tokens | Completion tokens | Total tokens | Sequential runtime | Cost |
|---|---:|---:|---:|---:|---:|---:|
| stage1 | 11,070 | 6,780,560 | 534,470 | 7,315,030 | 3.38h | $9.34 |
| stage2 | 36,900 | 22,601,867 | 1,781,567 | 24,383,434 | 11.28h | $31.13 |
| stage3 | 110,700 | 67,805,600 | 5,344,700 | 73,150,300 | 33.84h | $93.39 |
| full | 367,893 | 225,340,611 | 17,762,220 | 243,102,831 | 112.45h | $310.37 |

## Cost concentration

The measured dominant stage is **subjective_evaluation**. Affordability is a research-budget decision; this report does not authorize Stage 1.

Stage 1 projects to about **$9.34** and Full to about **$310.37** from this three-query sample. Without a supplied research-budget ceiling, affordability cannot be answered as a boolean. The full run is materially expensive and should remain gated; the three-query sample also cannot eliminate sampling uncertainty from unusually long or short benchmark sources.

## Pricing configuration

Configured USD per 1M input/output tokens: `{"gpt-3.5-turbo": [0.5, 1.5], "gpt-3.5-turbo-0125": [0.5, 1.5], "gpt-3.5-turbo-1106": [1.0, 2.0], "gpt-3.5-turbo-16k": [3.0, 4.0], "gpt-3.5-turbo-16k-0613": [3.0, 4.0], "gpt-3.5-turbo-instruct": [1.5, 2.0], "gpt-3.5-turbo-instruct:20230824-v2": [1.5, 2.0]}`. Actual response model identifiers, not merely requested aliases, determine the recorded cost.
