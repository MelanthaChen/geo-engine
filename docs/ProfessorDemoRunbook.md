# Professor Demo Runbook

## Demo identity

This is a **Princeton-style frozen new-website demo validation**. It is not GEO-Bench replication.

| Item | Frozen demo value |
|---|---|
| Property | ID 1, `GeoAIResume` |
| Original stored deployment | `https://geoairesume-web-six.vercel.app/` — deleted Vercel deployment |
| Source repository | `https://github.com/MelanthaChen/geoairesume-web` |
| Stable local demo URL | `http://127.0.0.1:8000/` |
| Target article | `Resume Gap Explanation Guide` |
| Target rank/index | Rank 1, zero-based index 0 |
| Query policy | `geoairesume-resume-gap-query-v1` |
| Evaluation query | `how to explain gaps in employment on your resume` |
| Workflow label | `princeton-style-frozen-new-website-demo-validation-v1` |

The original property was stored in the `properties` table as property 1 and in `backend/app/services/property_service.py` as the seeded default. The same URL also appeared as the example domain in both property-dialog components. That Vercel deployment now returns `DEPLOYMENT_NOT_FOUND`. The repository's public GitHub metadata identifies the source as `MelanthaChen/geoairesume-web`; its old declared Vercel homepage is also deleted.

For a stable local demonstration, property 1 now points to a local frozen rendering of the real repository article. Its text is copied from `src/data/expandedArticles.ts`, and validation refuses to run if its SHA-256 differs from the frozen manifest.

## Why this query is defensible

The target repository contains a dedicated `resume-gap-explanation-guide` article. Its stated intent is to explain resume gaps with clarity, professionalism, and role-relevant evidence. The frozen query is also present in the project's official GEO-Bench cache, allowing four matching real reference snapshots to be reused without live retrieval.

Supporting evidence is stored with every experiment:

- source repository;
- source file and article slug;
- audit ID;
- selected audit recommendation ID;
- audit brand and product summaries;
- primary professional intent.

## Frozen five-source set

| Rank | Role | URL | SHA-256 |
|---:|---|---|---|
| 1 | Audited target | `http://127.0.0.1:8000/` | `83d7f3a6571ff7e8d4bd42e72460a8a687f9acadfd6ffa97ed023d61fb6cffb2` |
| 2 | Reference | `https://hbr.org/2023/06/how-to-explain-a-gap-in-your-resume` | `035cb9219440cec20bdd2a29565f0ff77bf5d15c16b9dd5cad80a24e224ba8d8` |
| 3 | Reference | `https://novoresume.com/career-blog/employment-gap-in-resume` | `f9168fe05894b3b1a3fc7fa9f357514ab3eecb011f33455300f92e1df2006276` |
| 4 | Reference | `https://www.grammarly.com/blog/resume-gap/` | `21c39c1c1fb346bc38b55442517c14e35165a8f7d0ff584b37ce41b98ffd098d` |
| 5 | Reference | `https://www.umassglobal.edu/news-and-events/blog/how-to-explain-gaps-in-employment` | `db2c47e440d73e01f969c616922c07c145a62bd936e55c3d367c1bd889c89b8e` |

The four reference texts are the full usable cleaned snapshots already stored in `backend/experiment_dataset/geo_bench/test.jsonl`, row index 547. The demo loader validates the query, URLs, source count, ordering, and all hashes before creating an experiment. The frozen timestamp is `2026-09-23T19:45:00Z`.

## Expected UI flow

1. Open **Website Audit**.
2. Use the property selector to choose **GeoAIResume — http://127.0.0.1:8000**.
3. Click **Analyze Website**.
4. Confirm the page shows **Audit complete**, 15 structured features, and optimization opportunities.
5. Click **Continue to Optimization**.
6. Confirm Predictor shows website 1, the new audit ID, 15 features, and the received opportunities.
7. Click **Validate**.
8. Confirm **Teacher Validation** appears with Running status and answer-sample progress.
9. Wait for automatic navigation to **Teacher Pipeline**.
10. Confirm Pipeline Status is **Ready**, Pending Experiments is 0, and the latest experiment matches the run just completed.
11. Click **Export JSONL**.
12. Click **Export CSV**.

Experiment Lab, Google Search, a worker command, and terminal interaction are not required.

## Expected timings

| Stage | Typical local time |
|---|---:|
| Select property and load prior audit | Under 2 seconds |
| Fresh Website Audit | Under 2 seconds |
| Continue to Optimization | Under 2 seconds |
| Freeze and integrity-check five sources | Under 1 second |
| Baseline: five Teacher answers | Approximately 10–25 seconds |
| Rewrite and treatment: five Teacher answers | Approximately 15–35 seconds |
| Teacher Pipeline and dataset version | Under 3 seconds after experiment completion |
| JSONL or CSV download | Under 2 seconds |

Allow approximately one minute for the complete demonstration. OpenAI response latency can vary.

## What the professor should see

- GeoAIResume remains the selected property through Audit and Predictor.
- Audit context moves to Predictor without re-entry.
- Validate immediately creates a Teacher Validation experiment; it never opens Experiment Lab.
- Status advances from Running to Completed.
- Teacher Pipeline opens automatically.
- Dataset version increments on each successful repeat.
- Each run adds five immutable Teacher samples because five treatment answers are paired with their five baseline answers.
- Export buttons are visible whenever a dataset exists.

The persisted experiment will show exactly five sources, target rank 1, five `original` runs, five `fluency` runs, and a non-fabricated measured metric delta for each answer pair.

## Recovery steps

### Audit fails

1. Confirm the backend health endpoint responds at `http://127.0.0.1:8000/health`.
2. Reload Website Audit.
3. Re-select GeoAIResume.
4. Click **Analyze Website** again.

The frozen target page is served by the running backend, so no external website deployment is required.

### Validation fails

1. Read the error displayed in the Teacher Validation panel.
2. Confirm OpenAI authentication is available; frozen reference loading requires no Google credentials.
3. Return to Website Audit and run a fresh audit.
4. Continue to Optimization and click Validate again.

An integrity error means a frozen target or reference no longer matches its manifest. Do not bypass it; restore the checked-in source/cache content.

### Dataset does not refresh

1. Wait several seconds after experiment completion.
2. Open **Teacher Pipeline** from the sidebar.
3. Confirm Pending Experiments is 0 and Last Experiment is the completed experiment.
4. Reload the page if necessary.

### Export does not download

Open Teacher Pipeline and use its **Export JSONL** and **Export CSV** links. Both call the latest immutable dataset export endpoint directly.

## Reset and repeat

No database reset is required or recommended. Dataset versions are immutable and cumulative.

To repeat the demonstration entirely through the web interface:

1. Return to Website Audit.
2. Select GeoAIResume.
3. Run **Analyze Website** to create a new audit.
4. Continue to Optimization.
5. Click Validate.
6. Wait for Teacher Pipeline.
7. Download the newly versioned cumulative dataset.

Each successful repeat creates a new experiment, five new Teacher samples, and the next dataset version while preserving earlier results.

## Verified runs

| Run | Audit | Experiment | Baseline/treatment | Aggregate visibility delta | Samples added | Dataset |
|---:|---:|---:|---|---:|---:|---|
| 1 | 2 | 1 | 5 / 5 completed | `+0.3181716` | 5 | `teacher-dataset-v000001` |
| 2 | 3 | 2 | 5 / 5 completed | `+0.1439574` | 5 | `teacher-dataset-v000002` |

Latest JSONL and CSV exports each contain all 10 samples, including five records from experiment 2.
