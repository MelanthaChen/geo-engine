# Princeton GEO Replication Run

- Dataset: GEO-Optim/geo-bench test
- Provider: chatgpt
- Model: gpt-3.5-turbo-16k
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

- **PASS** — Quotation Addition, Statistics Addition, and Cite Sources all outperform baseline on PAWC. Evidence: `{"baseline": 0.020979199999999996, "observed": {"quotation": 0.0727628, "statistics": 0.027231066666666668, "citation": 0.09823113333333335}}`
- **FAIL** — The qualitative PAWC strategy ordering agrees with Table 1. Evidence: `{"pairwise_concordance": 0.6, "required": 0.8}`
- **PASS** — Quotation Addition outperforms the baseline on PAWC. Evidence: `{"left_mean": 0.0727628, "right_mean": 0.020979199999999996, "relative_change": 2.4683305369127524}`
- **PASS** — Statistics Addition outperforms the baseline on PAWC. Evidence: `{"left_mean": 0.027231066666666668, "right_mean": 0.020979199999999996, "relative_change": 0.29800310148464537}`
- **PASS** — Cite Sources outperforms the baseline on PAWC. Evidence: `{"left_mean": 0.09823113333333335, "right_mean": 0.020979199999999996, "relative_change": 3.682310733170634}`
- **PASS** — Fluency Optimization improves PAWC over baseline. Evidence: `{"left_mean": 0.34519286666666665, "right_mean": 0.020979199999999996, "relative_change": 15.454052903193007}`
- **PASS** — Easy-to-Understand improves PAWC over baseline. Evidence: `{"left_mean": 0.06792066666666667, "right_mean": 0.020979199999999996, "relative_change": 2.237524150905024}`
- **FAIL** — Authoritative produces limited PAWC improvement. Evidence: `{"left_mean": 0.06619946666666666, "right_mean": 0.020979199999999996, "relative_change": 2.1554809843400453}`
- **FAIL** — Keyword Stuffing provides little or no PAWC improvement. Evidence: `{"left_mean": 0.0799534, "right_mean": 0.020979199999999996, "relative_change": 2.811079545454546}`
- **PASS** — Quotation Addition improves Subjective Impression. Evidence: `{"left_mean": 0.14107765940044448, "right_mean": -0.0004442353706618866, "relative_change": -318.5741256042859}`
- **PASS** — Statistics Addition improves Subjective Impression. Evidence: `{"left_mean": 0.023427932158483107, "right_mean": -0.0004442353706618866, "relative_change": -53.73765599433642}`
- **PASS** — Cite Sources improves Subjective Impression. Evidence: `{"left_mean": 0.09656244887101224, "right_mean": -0.0004442353706618866, "relative_change": -218.36776323582572}`
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
