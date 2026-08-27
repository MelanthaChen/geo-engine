# Princeton GEO Replication Run

- Dataset: GEO-Optim/geo-bench test
- Provider: chatgpt
- Model: gpt-3.5-turbo
- Strategies: 10
- Completed samples: 150/150
- Subjective samples calibrated: 150/150
- Methodological fidelity: high
- Model fidelity: partial (current alias is not the historical checkpoint)
- Result fidelity: ready for comparison
- Trend fidelity: ready for comparison

## Reproducible outputs

`runs.csv` contains sample-level provenance and metrics; `paper_metrics.csv` contains strategy-level paper metrics; `paper_objective_metrics.png` reproduces the objective-method comparison as a PNG. Paper-oriented means and deviations are expressed on the paper's 0–100 display scale.

## Published comparison anchors

Table 1 reports No Optimization PAWC 19.3, Quotation Addition 27.2 and Statistics Addition 25.2. Numerical agreement must be assessed only after the full run; current model aliases prevent an exact-checkpoint claim.

## Known deviations

The public test split has three rows without Top-5 sources. Subjective scores use the public GPT-3.5-instruct/logprob procedure when enabled; exact historical model snapshots and numeric seeds are unavailable.

## Paper Conclusion Verification

Trend similarity: 75.0%. Stage decision: **STOP** (threshold 90%).

- **PASS** — Quotation Addition, Statistics Addition, and Cite Sources all outperform baseline on PAWC. Evidence: `{"baseline": 0.07261246666666667, "observed": {"quotation": 0.1189942, "statistics": 0.08777626666666666, "citation": 0.15150860000000002}}`
- **FAIL** — The qualitative PAWC strategy ordering agrees with Table 1. Evidence: `{"pairwise_concordance": 0.5777777777777777, "required": 0.8}`
- **PASS** — Quotation Addition outperforms the baseline on PAWC. Evidence: `{"left_mean": 0.1189942, "right_mean": 0.07261246666666667, "relative_change": 0.6387571647476511}`
- **PASS** — Statistics Addition outperforms the baseline on PAWC. Evidence: `{"left_mean": 0.08777626666666666, "right_mean": 0.07261246666666667, "relative_change": 0.2088319085703372}`
- **PASS** — Cite Sources outperforms the baseline on PAWC. Evidence: `{"left_mean": 0.15150860000000002, "right_mean": 0.07261246666666667, "relative_change": 1.0865370225682094}`
- **PASS** — Fluency Optimization improves PAWC over baseline. Evidence: `{"left_mean": 0.24912966666666667, "right_mean": 0.07261246666666667, "relative_change": 2.4309489555053445}`
- **PASS** — Easy-to-Understand improves PAWC over baseline. Evidence: `{"left_mean": 0.08583066666666667, "right_mean": 0.07261246666666667, "relative_change": 0.18203761153961623}`
- **FAIL** — Authoritative produces limited PAWC improvement. Evidence: `{"left_mean": 0.13336746666666668, "right_mean": 0.07261246666666667, "relative_change": 0.8367020539172798}`
- **FAIL** — Keyword Stuffing provides little or no PAWC improvement. Evidence: `{"left_mean": 0.12299833333333332, "right_mean": 0.07261246666666667, "relative_change": 0.6939010472949088}`
- **PASS** — Quotation Addition improves Subjective Impression. Evidence: `{"left_mean": 0.1665480709435866, "right_mean": 0.07298605257300178, "relative_change": 1.2819164083028416}`
- **PASS** — Statistics Addition improves Subjective Impression. Evidence: `{"left_mean": 0.11214112606991881, "right_mean": 0.07298605257300178, "relative_change": 0.5364733687680057}`
- **PASS** — Cite Sources improves Subjective Impression. Evidence: `{"left_mean": 0.08015677929648361, "right_mean": 0.07298605257300178, "relative_change": 0.09824790450626933}`
- **NOT_TESTED** — Lower-ranked sources benefit more from GEO. Evidence: `{"reason": "Requires separate rank_analysis experiment."}`
- **NOT_TESTED** — The most effective GEO method varies by domain and query type. Evidence: `{"reason": "Requires separate tag_analysis experiment."}`
- **NOT_TESTED** — Fluency plus Statistics is the strongest tested pair. Evidence: `{"reason": "Requires separate pairwise experiment."}`
- **NOT_TESTED** — High-performing GEO methods generalize to Perplexity.ai. Evidence: `{"reason": "Requires separate perplexity experiment."}`

## Replication Confidence

- Method Fidelity: 98.0%
- Implementation Fidelity: 96.0%
- Dataset Fidelity: 99.7%
- Evaluation Fidelity: 96.0%
- Trend Fidelity: 75.0%
- Model Fidelity: Unknown
- Model Fidelity note: Unknown: the historical GPT-3.5 checkpoint is unavailable.
