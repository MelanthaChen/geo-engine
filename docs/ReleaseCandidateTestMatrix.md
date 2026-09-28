# GEO Engine Release-Candidate Stabilization Matrix

Date: 2026-09-27  
Scope: local disposable PostgreSQL and local browser harness only. No deployment,
production mutation, or paid model call was performed.

## Release results

| ID | Component | Test performed | Result | Regression found | Fix | Final status |
|---|---|---|---|---|---|---|
| A | Property management | Actual FastAPI create/list/read/metrics against PostgreSQL | Expected routes returned 200; duplicate domains returned the expected conflict | None | None | Pass |
| B | Audit discovery | Real local sitemap/robots HTTP fixture plus a 140-route service/API fixture | Normal site discovered 3 URLs; SPA discovered and requested 140 | None in final pass | None | Pass |
| C | Important GEO pages | Candidate ranking, audited URL retention, inbound links, content richness, family diversity, deterministic output | 30 distinct SPA pages retained across `/guide`, `/comparison`, and `/resources`; focused selection tests passed | None | None | Pass |
| D | HTTP extraction | Normal multi-page HTML through `POST /api/v1/audit/run` | Four requested, four unique, all HTTP extraction, persisted and serialized | None | None | Pass |
| E | Browser/SPA fallback | 140 identical 328-word shells with distinct rendered DOM through Audit API | 30 bounded browser pages retained; 110 confirmed shells excluded | HTTP-only audits instantiated the browser wrapper unnecessarily | Return before browser construction when neither fallback candidates nor suspicious clusters exist | Pass |
| F | Evidence extraction | Metadata, headings, canonical, extraction method, links, authorship/date, schema, FAQ, quantitative, citation, quotation, readability, lexical, and prominent-term tests | Persistence and serialization passed; browser provenance visible in UI | None | None | Pass |
| G | Opportunities | FAQ, citation, authority, heading, metadata, and transport/extraction failure fixtures | Opportunities contain factual evidence, affected/evaluated counts, affected URLs, and no predicted gain | None | None | Pass |
| H | Predictor handoff | Browser flow from fresh Audit #8 plus frontend strategy/API contract tests | URL and state carried audit #8; recommendation visible; override list included all ten treatments and excluded `original` | None | None | Pass |
| I1 | FAQ treatment | `ExperimentService._execute_query_seed` with a grounded FAQ rewrite plan, full-document application, source freezing, generation/evaluation, and repository handoff | Grounded paraphrase passed; unsupported factual additions remained rejected | Fresh generations could still accept a legacy full-document blob | Require `rewrite-plan-v1` for fresh treatments; retain legacy cache read compatibility only | Pass |
| I2 | Statistics treatment | Same application execution path with structured statistics operations and full-document validation | Complete optimized document persisted and remained consumable by Teacher Pipeline | Same shared rewrite-contract regression | Same shared rewrite-contract fix | Pass |
| I3 | Citation treatment | Same application execution path with structured citation operations and full-document validation | Complete optimized document persisted and remained consumable by Teacher Pipeline | Same shared rewrite-contract regression | Same shared rewrite-contract fix | Pass |
| I4 | Quotation treatment | Same application execution path with structured quotation operations and full-document validation | Complete optimized document persisted and remained consumable by Teacher Pipeline | Same shared rewrite-contract regression | Same shared rewrite-contract fix | Pass |
| I5 | Authoritative treatment | Same application execution path with structured authoritative operations and full-document validation | Complete optimized document persisted and remained consumable by Teacher Pipeline | Same shared rewrite-contract regression | Same shared rewrite-contract fix | Pass |
| I6 | Easy to Understand treatment | Same application execution path with structured simplification operations and full-document validation | Complete optimized document persisted and remained consumable by Teacher Pipeline | Same shared rewrite-contract regression | Same shared rewrite-contract fix | Pass |
| I7 | Fluency treatment | Same application execution path with structured fluency operations and full-document validation | Complete optimized document persisted and remained consumable by Teacher Pipeline | Same shared rewrite-contract regression | Same shared rewrite-contract fix | Pass |
| I8 | Unique Words treatment | Same application execution path with structured lexical operations and full-document validation | Complete optimized document persisted and remained consumable by Teacher Pipeline | Same shared rewrite-contract regression | Same shared rewrite-contract fix | Pass |
| I9 | Technical Terms treatment | Same application execution path with structured terminology operations and full-document validation | Complete optimized document persisted and remained consumable by Teacher Pipeline | Same shared rewrite-contract regression | Same shared rewrite-contract fix | Pass |
| I10 | Keyword Stuffing treatment | Same application execution path with structured keyword operations and full-document validation | Complete optimized document persisted and remained consumable by Teacher Pipeline | Same shared rewrite-contract regression | Same shared rewrite-contract fix | Pass |
| J | Retrieval providers | Exa request/order/error tests; Brave and Google compatibility tests | Exa default passed; missing key, empty results, timeout, auth, rate limit, and provider outage are actionable | Injected targets were stamped with the external retrieval provider | Mark target `injected_for_controlled_experiment`; provider label remains only on references | Pass |
| K | Source-set freezing | Compared query, source URLs/order/hashes, target rank, references, and prompts for baseline/treatment | Same five sources and configuration; only Source 1 text changed | None | None | Pass |
| L | Teacher execution | PostgreSQL experiment with actual repository/service/evaluator and deterministic network doubles; browser-triggered Experiment #4 | Completed automatically with ten runs and no worker/Experiment Lab interaction | Rewrite plan was not propagated into run/sample provenance | Store the plan with generation parameters and expose it in Teacher provenance | Pass |
| M | Repetitions | One context, five baseline and five treatment answers | API/UI showed one unique context, five repetitions, five answer pairs, and `repetition 5/5` | None | None | Pass |
| N | Teacher Pipeline | Automatic collection after experiment completion, status, samples, grouped browser view | One formal sample generated for five pairs; browser displayed grouped experiment and aggregate metrics | None | None | Pass |
| O | 100 contexts | Deterministic mocked audit generator over 40 pages/eight families | 100 unique queries and 100 unique context fingerprints; default one repetition; eight families represented | None | None | Pass |
| P | Dataset construction | PostgreSQL membership inspection and duplicate-context tests | Unique constraint and writer produce one formal membership per dataset/fingerprint | Clean replay saw the current-model column before 0028 because legacy revision 0001 calls `create_all` | Make 0028 reconcile its owned column/index/constraint deterministically | Pass |
| Q | CSV export | Generated from actual persisted Teacher dataset, parsed again with `csv.DictReader` | One row for one unique context; five repetitions decoded; provenance/strategy retained | None | None | Pass |
| R | JSONL export | Generated from actual persisted Teacher dataset and parsed line by line | One metadata object and one formal sample; plan/document separated; legacy scores absent | None | None | Pass |
| S | Migrations | Empty PostgreSQL 0001→0028, simulated stale 0025/26 repair, simulated old 0027→0028, one-head check, exact ORM/schema comparison | All paths reached `20260927_0028`; one head; six critical tables exactly matched ORM | 0028 initially raised duplicate-column on clean replay due legacy 0001 behavior | Safe ownership checks in 0028 for its column/index/constraint | Pass |
| T | Frontend professor flow | Actual Vite browser: property → clean Audit → Analyze → evidence → Continue → strategy → Validate → progress → Teacher Pipeline → exports | Audit #8 and Experiment #4 completed; automatic navigation reached dataset v000002; required labels/tooltips/controls visible | A component-test harness hung before collection | Replaced it with browser testing of the real page/API flow and deterministic external-call doubles | Pass |
| U | CORS/API | Production Vercel origin preflight, success, and 404 error; unrelated origin | Allowed origin received exact allow-origin on success/error; unrelated origin preflight returned 400 without allow-origin | None | None | Pass |
| V | Historical records | Historical generation params and samples without new provenance fields; old audit fallback serialization | Old records remained readable and no history was deleted | None | Compatibility readers retained | Pass |
| W | Error states | Missing/rate-limited/empty provider, browser timeout, extraction failure, malformed plan, missing anchor, FAQ grounding, no evidence, unsupported strategy | Failures were actionable and invalid output did not enter datasets | Missing anchor and malformed-plan paths lacked application-contract coverage | Added explicit rewrite error tests | Pass |

## Integrated observations

- Normal HTML API audit: 4 discovered/requested/unique pages, 4 HTTP pages,
  zero browser pages; latest and exact-audit retrieval used the created audit ID.
- SPA API audit: 140 discovered, 140 requested, 30 bounded browser-rendered
  unique pages, 110 shared-shell responses excluded, 30 persisted pages.
- Five-repetition PostgreSQL experiment: 10 run records, one unique training
  context, five repetitions, one dataset membership, one CSV row, one JSONL
  training object.
- Browser professor flow: fresh Audit #8, exact Predictor handoff, Exa shown,
  Experiment #4 completed at repetition 5/5, automatic Teacher collection,
  dataset `teacher-dataset-v000002`, grouped result, CSV and JSONL controls.
- The browser harness used deterministic doubles only for external retrieval and
  teacher-model network traffic. FastAPI, PostgreSQL, crawling, extraction,
  evaluation, persistence, dataset construction, routing, polling, and UI were
  the real application paths.

## Final command results

- Backend tests: `170 passed`.
- Frontend tests: `28 passed` across 9 files.
- Frontend lint: pass.
- Frontend production build: pass (non-blocking existing bundle-size warning).
- Python compilation: pass.
- Alembic heads/current: exactly `20260927_0028 (head)`.
- Clean PostgreSQL replay: pass, 0001 → 0028.
- Stale-production repair: pass; both `evidence_json` columns restored.
- 0027 → 0028 simulation: pass; fingerprint column/index/unique constraint restored.
- Final ORM/schema equality: pass for `website_audits`, `website_pages`,
  `website_audit_recommendations`, and all three Teacher dataset tables.
- SPA E2E: pass through the Audit API.
- All ten strategies E2E: pass through the application execution path.
- 100-context mocked flow: pass with 100 distinct fingerprints.
- CSV parsed: pass.
- JSONL parsed: pass.

## Non-blocking notes

- Vite reports a 620 kB minified application chunk; code splitting can be handled
  after the demo freeze.
- The Teacher page's property-scoped context count and global latest-dataset
  manifest count can differ when the local database contains other properties.
  Both labels are factual, but the scope distinction can be made more explicit
  after the release freeze.
