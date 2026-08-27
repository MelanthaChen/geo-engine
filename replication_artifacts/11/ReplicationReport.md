# Princeton GEO Replication Run

- Dataset: GEO-Optim/geo-bench test
- Provider: chatgpt
- Model: gpt-3.5-turbo-16k
- Strategies: 10
- Completed samples: 1500/1500
- Subjective samples calibrated: 1500/1500
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

Trend similarity: 58.3%. Stage decision: **STOP** (threshold 80%).

- **FAIL** — Quotation Addition, Statistics Addition, and Cite Sources all outperform baseline on PAWC. Evidence: `{"baseline": 0.21267653333333333, "observed": {"quotation": 0.24251219333333335, "statistics": 0.17913518666666667, "citation": 0.25954039333333334}}`
- **FAIL** — The qualitative PAWC strategy ordering agrees with Table 1. Evidence: `{"pairwise_concordance": 0.7333333333333333, "required": 0.8}`
- **PASS** — Quotation Addition outperforms the baseline on PAWC. Evidence: `{"left_mean": 0.24251219333333335, "right_mean": 0.21267653333333333, "relative_change": 0.14028656350739846}`
- **FAIL** — Statistics Addition outperforms the baseline on PAWC. Evidence: `{"left_mean": 0.17913518666666667, "right_mean": 0.21267653333333333, "relative_change": -0.15771061405301573}`
- **PASS** — Cite Sources outperforms the baseline on PAWC. Evidence: `{"left_mean": 0.25954039333333334, "right_mean": 0.21267653333333333, "relative_change": 0.22035275479382152}`
- **PASS** — Fluency Optimization improves PAWC over baseline. Evidence: `{"left_mean": 0.26661898, "right_mean": 0.21267653333333333, "relative_change": 0.25363610089563243}`
- **FAIL** — Easy-to-Understand improves PAWC over baseline. Evidence: `{"left_mean": 0.19791939333333333, "right_mean": 0.21267653333333333, "relative_change": -0.06938772119663415}`
- **PASS** — Authoritative produces limited PAWC improvement. Evidence: `{"left_mean": 0.22379396, "right_mean": 0.21267653333333333, "relative_change": 0.05227387569479528}`
- **PASS** — Keyword Stuffing provides little or no PAWC improvement. Evidence: `{"left_mean": 0.1442825533333333, "right_mean": 0.21267653333333333, "relative_change": -0.3215868668162105}`
- **PASS** — Quotation Addition improves Subjective Impression. Evidence: `{"left_mean": 0.2713372879834896, "right_mean": 0.2074118069413025, "relative_change": 0.30820560307002187}`
- **FAIL** — Statistics Addition improves Subjective Impression. Evidence: `{"left_mean": 0.18977094987961793, "right_mean": 0.2074118069413025, "relative_change": -0.08505232812844132}`
- **PASS** — Cite Sources improves Subjective Impression. Evidence: `{"left_mean": 0.25422075266220007, "right_mean": 0.2074118069413025, "relative_change": 0.22568120113887477}`
- **NOT_TESTED** — Lower-ranked sources benefit more from GEO. Evidence: `{"reason": "Requires separate rank_analysis experiment."}`
- **NOT_TESTED** — The most effective GEO method varies by domain and query type. Evidence: `{"reason": "Requires separate tag_analysis experiment."}`
- **NOT_TESTED** — Fluency plus Statistics is the strongest tested pair. Evidence: `{"reason": "Requires separate pairwise experiment."}`
- **NOT_TESTED** — High-performing GEO methods generalize to Perplexity.ai. Evidence: `{"reason": "Requires separate perplexity experiment."}`

## Replication Confidence

- Method Fidelity: 98.0%
- Implementation Fidelity: 96.0%
- Dataset Fidelity: 99.7%
- Evaluation Fidelity: 96.0%
- Trend Fidelity: 58.3%
- Model Fidelity: Unknown
- Model Fidelity note: Unknown: the historical GPT-3.5 checkpoint is unavailable.
