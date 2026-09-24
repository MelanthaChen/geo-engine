# Teacher Validation Methodology Audit

**Review date:** 2026-09-23  
**Scope:** Methodology and current implementation only. No application code or database state was changed.

## Executive conclusion

The platform contains two materially different experiment paths:

1. The **GEO-Bench path** is substantially a benchmark-replication path. It loads the stored query, stored five sources, and stored zero-based `sugg_idx`; it therefore does not need live Google Search during experiment execution.
2. The **Audit → Predictor → Teacher Validation path** is intended to be a new-website validation path, but it does not yet implement that methodology correctly. It generates one query from the first audit opportunity and uses live Google Search to obtain five documents. It does **not** insert the audited website into that source set or mark it as the optimization target. The experiment consequently rewrites a seeded random Google result, which may be unrelated to the audited website.

The current Teacher Validation path is therefore best classified as an **incomplete hybrid of new-website validation and generic live-search experimentation**, not GEO-Bench replication and not a valid controlled validation of the audited website.

## 1. Official Princeton GEO workflow

The Princeton GEO paper separates retrieval from the generative-engine experiment. GEO-Bench supplies a query and five cleaned source documents derived from the top Google results. For an experiment, one source is selected for optimization, the other sources remain fixed, and the generative engine answers using the same source set with either the original or modified version of that selected source. The paper generates multiple responses and evaluates visibility with objective and subjective metrics.

Key properties of the published workflow are:

- Each benchmark record already contains its query and five source documents.
- A single source is the optimization target; in the platform's published-data loader this identity is represented by zero-based `sugg_idx`.
- Baseline and treatment differ only in the content of that selected source. The query, source membership, source order, model configuration, and evaluation procedure must otherwise remain controlled.
- The answer prompt presents the query and the five sources and asks the model to synthesize an answer with citations.
- Multiple generated answers are evaluated because generative-model output is stochastic.
- GEO-Bench's Google results are an input-generation fact, not a requirement to search Google again every time the stored benchmark is replayed.

Primary sources:

- [GEO paper, experiment setup and GEO-Bench construction](https://arxiv.org/html/2311.09735)
- [Official GEO repository](https://github.com/GEO-optim/GEO)
- [Official GEO-Bench dataset](https://huggingface.co/datasets/GEO-Optim/geo-bench)

## 2. The two modes must remain distinct

### Mode 1 — GEO-Bench replication

**Scientific question:** Given a published benchmark query and its frozen source set, does changing the designated source with a GEO strategy reproduce the reported visibility effect?

Required input and controls:

- Stored GEO-Bench query.
- Stored five cleaned sources in their stored order.
- Stored `sugg_idx`, identifying exactly which source is modified.
- Frozen baseline source text and treatment rewrite.
- Identical four non-target sources in baseline and treatment.
- Identical prompt template, model/provider parameters, sampling protocol, metrics, and evaluator versions.
- Repeated answer generation and recorded random/sampling configuration.

**Retrieval rule:** Do not perform live Google Search. Live retrieval would introduce time-dependent documents, ranks, and content and would cease to be a replication of that benchmark record.

### Mode 2 — New-website Teacher validation

**Scientific question:** For a particular audited page and evaluation query, does a specified rewrite of that page improve its visibility when all competing/reference sources are held fixed?

This is an extension of the Princeton experimental design, not a literal GEO-Bench replication. A defensible workflow is:

1. Select the exact audited target page and freeze its original content.
2. Generate or select a versioned set of evaluation queries relevant to that page.
3. Retrieve and freeze relevant competing/reference documents under a recorded retrieval protocol.
4. Construct a five-document source set that deterministically includes the audited target page.
5. Record the target's source index, analogous to `sugg_idx`.
6. Build the baseline using the original target content.
7. Build the treatment by replacing content in that same source slot with the proposed rewrite; keep the other four documents unchanged.
8. Generate multiple Teacher answers under the same model and sampling conditions for baseline and treatment.
9. Evaluate the target source's visibility/citation outcomes.
10. Persist raw inputs, raw outputs, metrics, uncertainty/aggregation results, and treatment-minus-baseline deltas.

If the target site is not naturally in the retrieved top five, forcibly inserting it is a methodological adaptation. The protocol must explicitly state whether it uses target plus four references, replaces a predefined retrieved rank, or excludes such queries. That choice must be versioned because it changes the estimand.

## 3. Current implementation audit

### 3.1 Audit-to-validation frontend behavior

The Predictor page receives an audit and selects only `audit.optimization_opportunities[0]`. It maps that opportunity to an existing GEO strategy and calls `startAuditValidation`.

`startAuditValidation` then:

- Creates exactly one query from the hard-coded template: `What information does {propertyName} provide about {opportunityTitle}?`
- Starts `/api/v1/experiment-lab/run`.
- Sets `dataset` to `custom`.
- Sends `queries: [query]`.
- Sends `dataset_documents: null`.
- Requests baseline `original` and one treatment strategy.
- Uses seed 42, temperature 0.7, and visibility/citation-related metrics.

The audit ID, website ID, website URL, and opportunity explanation provide UI/linkage context, but the audited page content is not included in the experiment request.

### 3.2 Why it calls Google Search

The call is a direct consequence of the request shape, not a Princeton requirement for every experiment:

1. The request declares a `custom` dataset, so the backend does not load GEO-Bench.
2. It supplies a string query but `dataset_documents` is `null`.
3. The experiment service consequently has no stored documents for that query.
4. `GenerativeEngineService` uses its default `GoogleSearchProvider` whenever `retrieved_documents` is `None`.
5. It asks Google for five documents because the engine enforces a five-source Princeton-style prompt.

Thus Google Search is currently being used as an implicit fallback source-set builder for a custom query. It is not being called to reproduce a frozen GEO-Bench row.

### 3.3 What source is actually optimized

After retrieval, the engine first looks for a document marked `is_optimization_target`. Google-retrieved documents are not supplied with an audited-site target designation. When no target is marked, the code chooses one of the five documents with `random.Random(random_seed).choice(documents)`.

The result is critical:

- The audited website is not fetched and inserted by this workflow.
- The audited website is not guaranteed to appear in the search results.
- Even if it appears, it is not guaranteed to be selected.
- The rewrite and visibility evaluation apply to the randomly selected result, not necessarily the audited website.
- The subsequent Teacher sample combines audit-derived website features with metrics from the selected search result. This can create a semantically invalid training pair.

### 3.4 Controlled experiment behavior that is already present

Once a target document has been chosen, the lower-level engine does preserve several Princeton-style controls:

- It uses five documents.
- It replaces the selected source in the same prompt position for each strategy.
- It generates five answers per strategy.
- It records prompts, answers, selected rank, documents, and evaluated metrics.
- It pairs baseline and treatment runs at the same sample index before creating Teacher samples.

These mechanics are useful, but they do not repair incorrect target selection upstream.

### 3.5 Existing GEO-Bench replication path

For `dataset_name == "geo_bench"`, `GeoBenchLoader` reads the official cached/downloaded JSONL, validates that each row has a query, at least five sources, and a valid `sugg_idx`, then marks `sources[sugg_idx]` as `is_optimization_target`. These documents are passed into the generative engine as `retrieved_documents`.

Because documents are provided, the default Google provider is not invoked. The engine honors the marked target rather than selecting a random source. This is the correct architectural distinction for benchmark replication.

## 4. Evaluation-query provenance for website-only input

### Current behavior

There is no research-grade website query-generation or query-selection subsystem. The current workflow takes the first audit optimization opportunity and produces one query from the property name and opportunity title using a fixed UI string template.

This is not part of the official Princeton methodology. The paper begins with benchmark queries; it does not specify how to derive evaluation queries from a previously unseen website.

### Methodologically required behavior

For new websites, evaluation queries need an explicit, versioned policy. Candidate inputs can include:

- The target page's primary topic, entities, claims, and user intents extracted by the audit.
- Existing first-party query data, when available and consented (for example, search analytics).
- A deterministic query-template library.
- A versioned LLM query generator followed by documented filtering/selection.
- A fixed mix of branded, non-branded, informational, comparison, and decision queries appropriate to the page.

For every selected query, provenance should include generator/model and version, prompt/template version, source evidence, selection criteria, rejected candidates or selection trace, timestamp, and a stable query-set version. Queries must be frozen before baseline/treatment comparison.

## 5. Inserting the audited website into a Princeton-style source set

### Current behavior

It is not inserted. The URL appears only in the experiment description. No audited content is sent as a document, and no source is designated as the audited target.

### Required controlled construction

For each query:

1. Resolve the exact canonical audited page and snapshot its full relevant source text.
2. Retrieve and snapshot reference sources using a declared provider, region/language, date, parameters, and ranking response.
3. Apply a predetermined source-set policy to produce exactly five documents. Prefer an explicit target-plus-four-reference design for website validation, or document a fixed replacement rule if starting from five retrieved references.
4. Place the audited page at a recorded, deterministic target index.
5. Mark only that source as the optimization target.
6. Store hashes and complete snapshots for all five documents.
7. In treatment prompts, replace only the target source text with the rewrite. Preserve query, source order, reference text, prompt template, model configuration, and evaluators.

This preserves the paper's core controlled-intervention principle while being honest that source-set construction is a new-website extension.

## 6. What becomes the training label

The current Teacher Pipeline pairs a completed `original` run and an optimized-strategy run when they share the experiment query, sample index, provider, and model. It stores:

- `original_metrics`
- `optimized_metrics`
- `delta_metrics`, calculated metric by metric as `optimized - original`

Therefore, the present supervised target is a **vector of observed per-run metric deltas**, including whichever recorded metrics are present (such as target visibility score, citation count, PAWC, position/word measures, and configured subjective evaluation measures).

The scientifically meaningful primary label for the requested new-website mode should be the treatment effect on **target-source visibility**, defined under a versioned metric and aggregation protocol. At minimum it should preserve:

- Per-answer baseline and treatment measurements.
- The pairing key or sampling design.
- Aggregated baseline and treatment estimates across repeated answers/seeds.
- `delta_visibility = optimized_target_visibility - baseline_target_visibility`.
- Citation and position deltas as named secondary labels.
- Sample count, dispersion/uncertainty, and evaluator/version metadata.

The delta is an experimental measurement under the recorded source set and Teacher configuration; it is not universal ground truth about the rewrite. In the current audit-driven path it is additionally invalid as a label for the audited website whenever the randomly selected search document is not that website.

## 7. Mode classification and gap matrix

| Requirement | GEO-Bench path | Current Audit Teacher Validation | Correct new-website mode |
|---|---|---|---|
| Query origin | Stored benchmark query | One UI template from first audit opportunity | Versioned website-relevant query set |
| Source origin | Stored GEO-Bench Top-5 | Live Google Top-5 | Frozen target page plus frozen references |
| Live Google needed at execution | No | Yes, due to missing documents | A retrieval service is needed to create references; Google specifically is optional |
| Target identity | Stored `sugg_idx` | Seeded random retrieved result | Explicit audited-page target index |
| Audited page guaranteed present | Not applicable | No | Yes |
| Baseline/treatment control | Same stored slot changed | Same chosen slot changed | Same audited-page slot changed |
| Multiple answers | Yes | Five per strategy | Yes, with recorded aggregation/uncertainty |
| Label | Metric differences | Per-run metric deltas for potentially wrong source | Target-visibility treatment effect plus secondary deltas |
| Overall classification | Benchmark replication | Incomplete hybrid | Not yet implemented |

## 8. Direct answers

### Is Google Search actually required for GEO-Bench replication?

**No.** The stored GEO-Bench query, five stored sources, and `sugg_idx` are the experimental inputs. Searching again would mutate the benchmark. Google was used to create the source data, but live Google Search is not required to replay it.

### Is Google Search required for new-website validation?

**Not specifically.** A declared retrieval process is normally required to assemble relevant competing/reference sources, and Google most closely mirrors GEO-Bench's original retrieval origin. However, Google can be replaced by another fixed, documented, versioned retrieval provider. The current implementation specifically calls Google because custom experiments provide no documents and `GoogleSearchProvider` is the backend default.

### Where do evaluation queries come from for a website-only input?

**Currently:** one query is synthesized in the frontend from the property name and the title of the first audit opportunity. **Scientifically:** the official paper does not define this extension. The platform needs a versioned query generation/selection protocol based on the audited page's topics, entities, intents, and optionally first-party query evidence, with the selected query set frozen before experimentation.

### How is the audited website inserted into the Princeton-style source set?

**Currently, it is not inserted.** Correct new-website validation must snapshot the exact audited page, construct a frozen five-source set containing it, record its target index, and replace only that slot with the rewrite in treatment prompts while keeping the other four sources unchanged.

### What exactly becomes the ground-truth training label?

**Currently:** for each paired answer sample, the Teacher Pipeline stores `optimized_metric - original_metric` for every available metric. **For a sound new-website dataset:** the primary label should be the measured change in the audited target source's visibility under the controlled treatment, preferably aggregated over repeated answers/seeds with uncertainty, while citation, position, PAWC, and subjective deltas remain explicitly versioned secondary labels.

## Final determination

Current Teacher Validation does **not** yet validate the audited website according to the proposed new-website methodology. It launches a custom-query, live-Google experiment and optimizes a seeded random retrieved source. The standalone GEO-Bench data path correctly avoids live Google and uses the stored `sugg_idx`; the audit-driven path must not be described as GEO-Bench replication.
