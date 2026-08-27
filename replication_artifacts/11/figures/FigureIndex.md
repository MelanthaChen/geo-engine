# Princeton GEO Stage 1 — Figure Index

All figures were generated from the completed experiment 11 artifacts. PNG files are exported at 300 DPI; SVG files retain vector text and geometry for papers and presentations.

## Shared provenance

- Stage 1 run metadata, status, counts, and timeline: `../replication.json`
- Sample-level result count and field availability: `../runs.csv`
- Stage 1 strategy PAWC means: `../paper_objective_metrics.csv`
- Stage 1 objective and subjective aggregate metrics: `../paper_metrics.csv`
- Claim status, evidence, trend similarity, fidelity, and stage decision: `../paper_conclusion_verification.json` and `../paper_conclusion_verification.csv`
- Human-readable cross-check: `../ReplicationReport.md`
- Princeton reference PAWC: Table 1, Overall Position-Adjusted Word Count column in [GEO: Generative Engine Optimization](https://arxiv.org/html/2311.09735#S3)
- Total API cost `$10.71`: supplied explicitly in the figure-generation specification. It is not stored in the experiment 11 files.

## Figures

### Figure 1 — Stage 1 Experiment Workflow

Files: `Figure01_Stage1_Workflow.png`, `Figure01_Stage1_Workflow.svg`

Shows the fixed GEO-bench workflow, the 30-query Stage 1 subset, ten strategies, one rewrite per target, five generated answers, evaluation, trend verification, and report output. Counts come from `replication.json` and `runs.csv`. Runtime is calculated from the `execution_started` and `completed` timeline timestamps: **2 h 51 m 41 s**. Total cost uses the supplied `$10.71` value.

### Figure 2 — Paper vs Stage 1

Files: `Figure02_Paper_vs_Stage1.png`, `Figure02_Paper_vs_Stage1.svg`

Grouped PAWC comparison on the same 0–100 scale. Stage 1 values come from `paper_objective_metrics.csv`; paper values are copied from the official paper's Table 1 Overall PAWC column. Nothing is inferred from rankings.

### Figure 3 — Strategy Ranking Comparison

Files: `Figure03_Strategy_Ranking.png`, `Figure03_Strategy_Ranking.svg`

Ranks all ten strategies by PAWC in the paper and Stage 1, connecting identical methods. It highlights Statistics, which moved from paper rank 2 to Stage 1 rank 8. Rankings are calculated directly from the values used in Figure 2.

### Figure 4 — PASS / FAIL Summary

Files: `Figure04_Claim_Summary.png`, `Figure04_Claim_Summary.svg`

Displays every claim and exact `PASS`, `FAIL`, or `NOT_TESTED` status in `paper_conclusion_verification.json`. The figure does not collapse or reinterpret duplicate objective/subjective claims.

### Figure 5 — Replication Fidelity

Files: `Figure05_Replication_Fidelity.png`, `Figure05_Replication_Fidelity.svg`

Radar plot of Dataset, Prompt, Method, Evaluation, Implementation, Model, and Trend fidelity. Dataset, Method, Evaluation, Implementation, and Trend values come from the verification JSON. Prompt Fidelity and Model Fidelity are **absent/unknown** in the Stage 1 artifact; both axes are deliberately unscored and labeled `UNKNOWN`, rather than presented as measured zeroes.

### Figure 6 — Stage 1 Statistics

Files: `Figure06_Stage1_Statistics.png`, `Figure06_Stage1_Statistics.svg`

Infographic of the measured run scale: 30 queries, ten strategies, five answers per strategy, 1,500 generated answers, and 10,500 subjective dimension scores (1,500 answers × seven dimensions). Runtime comes from the timeline. Average costs are arithmetic derivatives of the supplied total: `$10.71 / 30 = $0.357` per query and `$10.71 / 10 = $1.071` per strategy.

### Figure 7 — Cost Breakdown Data Gap

Files: `Figure07_Cost_Breakdown_Data_Gap.png`, `Figure07_Cost_Breakdown_Data_Gap.svg`

The requested exact Answer Generation / Strategy Rewrite / Subjective Evaluation pie chart cannot be produced from the saved Stage 1 artifacts. Every `input_tokens`, `output_tokens`, `total_tokens`, and `token_cost` field in all 1,500 `runs.csv` rows is blank, and `replication.json` contains no category totals. This figure documents that provenance gap and intentionally does **not** draw a pie chart or assign invented percentages.

### Figure 8 — Trend Similarity

Files: `Figure08_Trend_Similarity.png`, `Figure08_Trend_Similarity.svg`

Central Stage 1 decision figure. The **58.3%** trend fidelity, component fidelity scores, **STOP** decision, and 80% threshold come directly from `paper_conclusion_verification.json`. Model Fidelity remains `UNKNOWN` exactly as recorded.

### Figure 9 — Scientific Findings

Files: `Figure09_Scientific_Findings.png`, `Figure09_Scientific_Findings.svg`

Visual synthesis of directionally reproduced claims. Quotation, Citation, Fluency, Authoritative, and Keyword Stuffing are drawn from their `PASS` objective claim rows. Statistics and Easy-to-Understand are drawn from their `FAIL` rows. The bottom observation is a concise interpretation of those recorded Stage 1 outcomes under the current model.

### Figure 10 — Future Work

Files: `Figure10_Future_Work.png`, `Figure10_Future_Work.svg`

Roadmap showing the completed audits and Stage 1 run, followed by pending work. Pending items align with the `STOP` stage decision and the `NOT_TESTED` scopes in the verification artifact. It communicates planning status and does not assert new experiment results.

## Reproduction

Run from the repository root:

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/geo-stage1-mpl XDG_CACHE_HOME=/tmp/geo-stage1-cache \
  python3 replication_artifacts/11/figures/generate_figures.py
```

The generator reads the artifacts without modifying them and overwrites only the PNG/SVG files in this directory.
