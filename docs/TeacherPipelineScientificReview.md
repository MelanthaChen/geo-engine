# Teacher Pipeline Scientific Design Review

**Review date:** 2026-09-23  
**Scope:** Current Teacher Pipeline implementation, database migration, export contract, audit feature input, and upstream Princeton experiment records.  
**Review type:** Read-only scientific and architectural assessment. No implementation or database changes are included.

## Executive verdict

The current Teacher Pipeline is a useful **lineage index and experiment-metric snapshot**, but it is **not a sufficient supervised fine-tuning dataset** for Qwen, Llama, Mistral, Gemma, or another causal language model.

Its strongest properties are:

- explicit baseline/optimized pairing;
- immutable-intent sample and dataset records;
- original, optimized, and delta metric maps;
- audit feature snapshots;
- run, experiment, audit, prompt-version, evaluator-version, and selected-document identifiers;
- canonical provenance and manifest hashes;
- cumulative dataset membership.

Its blocking deficiencies are:

1. It does not define what the student is being trained to produce.
2. It does not store a model-ready input/target pair.
3. It omits the original selected document, rewritten document, complete prompts, and complete teacher responses from the sample/export.
4. It stores hashes of critical artifacts rather than the artifacts themselves or immutable content-addressed references.
5. It lacks dataset splits, leakage groups, quality/safety/factuality labels, licensing, and sample selection policy.
6. Its version labels are mostly constants or display strings rather than resolvable code/model artifacts.
7. It cannot reproduce an experiment independently of the mutable operational database and external model/search services.
8. The underlying rewrite strategies explicitly permit invented statistics, quotations, or citations in some prompts. Without factuality and policy gates, fine-tuning on those outputs risks teaching hallucination and metric gaming.
9. Its worker, version allocation, export authorization, storage, and governance controls are not enterprise-ready.

**Overall readiness:**

| Use | Current readiness |
|---|---|
| Research transparency dashboard | Partially sufficient |
| Audit/experiment lineage index | Useful foundation |
| Metric-analysis dataset | Partially sufficient, after leakage controls |
| Direct causal-LM SFT | Not sufficient |
| LoRA/QLoRA training | Not sufficient |
| Exact independent reproduction | Not sufficient |
| Publication-grade artifact release | Not sufficient |
| Multi-tenant enterprise deployment | Not sufficient |

The current dataset should not be described as “training-ready.” A more accurate description is **candidate experiment evidence awaiting training-view construction and scientific qualification**.

---

## 1. Current design under review

### 1.1 Current unit of data

The pipeline creates one `TeacherTrainingSample` for each unprocessed non-`original` experiment run that can be paired with an `original` run having the same:

- experiment query;
- `sample_index`;
- provider;
- model.

It requires a completed experiment, a property, a preceding completed website audit, non-empty responses, prompt-version relationships, evaluations, metrics, and a selected experiment document.

### 1.2 Data physically stored in a sample

The sample stores:

- UUID sample ID;
- property, experiment, optimized run, baseline run, query, and audit IDs;
- string audit version;
- JSON audit-derived feature vector;
- strategy;
- provider/model/model-version strings;
- prompt, evaluation, and metric-version strings;
- original, optimized, and delta metric JSON;
- provenance JSON and its SHA-256 hash;
- introduction dataset version and timestamp.

### 1.3 Critical data not stored in the sample

Although some of it remains in operational experiment tables, the sample and JSONL export do not contain:

- the original selected document text;
- the rewritten/optimized document text;
- the baseline raw prompt;
- the optimized raw prompt;
- the baseline teacher response;
- the optimized teacher response;
- all retrieved documents and their complete content;
- exact website page HTML/text snapshots;
- the prompt templates or their checksums;
- evaluator raw details;
- request/response IDs or immutable raw provider payloads;
- a student-training instruction, target, or message sequence.

The provenance object stores SHA-256 hashes for the selected document, prompts, and responses, but a hash verifies an artifact only after the artifact has been obtained; it cannot recover the artifact.

### 1.4 Current dataset versions

Each successful worker append creates a cumulative dataset version with ordered membership, model/metric strings, experiment/sample counts, a JSON manifest, and a manifest hash. The manifest contains sample IDs but not the samples' content/provenance hashes, schema definitions, selection policy, split assignment, exclusions, quality report, or source licenses.

---

# A. Can the current Training Sample directly support supervised fine-tuning of Qwen/Llama?

## Answer

**No.** It cannot directly support supervised fine-tuning.

Current Qwen guidance uses message records with `system`, `user`, and `assistant` roles, while Meta's Llama recipes expect a preprocessing layer that produces causal-LM inputs such as `input_ids`, `attention_mask`, and `labels`. Gemma describes tuning data as input/expected-response pairs. These formats differ operationally but share one requirement: the training example must contain the actual input and expected output, not just feature/metric metadata. See [Qwen SFT data preparation](https://qwen.readthedocs.io/en/v3.0/training/ms_swift.html), [Meta Llama custom datasets](https://github.com/meta-llama/llama-cookbook/blob/main/getting-started/finetuning/datasets/README.md), and [Gemma fine-tuning](https://ai.google.dev/gemma/docs/tune).

The present export has neither a canonical conversation nor a text input/target pair. It is therefore not consumable without recovering upstream operational rows and inventing a task-specific transformation.

## Missing fields required before direct SFT

### Task definition

- `training_task_type`, for example `rewrite_document`, `select_strategy`, `generate_answer`, or `explain_optimization`;
- `training_objective_version`;
- exact definition of what the model input represents;
- exact definition of what tokens are supervised as the target;
- `sample_eligibility_policy_version`;
- `target_selection_policy` when multiple teacher artifacts exist.

Without these fields, the same record could be interpreted as at least four incompatible learning problems.

### Canonical model-neutral SFT content

- `system_instruction` or a versioned, resolvable reference plus immutable content hash;
- `user_instruction`;
- `input_context` containing the actual source content and applicable website features;
- `assistant_target` containing the exact desired output;
- preferably canonical `messages[]` with roles and ordered content;
- content language and locale;
- multi-turn boundaries if relevant;
- explicit end-of-example semantics;
- a flag describing whether reasoning traces are included, excluded, or unavailable.

### Source and rewrite artifacts

- exact original selected document text;
- exact rewritten document text;
- exact baseline answer;
- exact optimized answer;
- exact baseline and optimized prompts, including system prompts;
- original and rewritten content hashes;
- normalization/cleaning procedure and version;
- transformation/patch representation;
- truncation performed before teacher generation, if any;
- source URL snapshot timestamp and immutable artifact reference.

### Training control metadata

- train/validation/test split;
- leakage group IDs for property/domain, query/topic, selected document, experiment, campaign, and near-duplicate cluster;
- sample weight;
- include/exclude decision and reason;
- quality score and quality-gate version;
- sequence/token length under each intended tokenizer or a reproducible way to compute it;
- loss mask policy (for example, assistant-only loss);
- maximum-context handling policy;
- deduplication cluster and duplicate status.

### Safety, truthfulness, and rights

- factuality label;
- semantic-preservation label comparing source and rewrite;
- fabricated-claim/statistic/quotation/citation flags;
- citation validity label;
- harmful-content and policy labels;
- PII/secrets detection outcome;
- source license/terms, copyright status, and permitted training use;
- consent/data-origin classification;
- deletion/retention/legal-hold status.

### Preference or ranking data, if desired

SFT needs a chosen target. If the intended later objective is preference optimization or candidate ranking, also store:

- chosen and rejected outputs;
- pairwise preference label;
- judge identity/version and rubric;
- preference strength/confidence;
- tie/abstention state;
- adjudication record.

Metric deltas alone cannot substitute for these fields.

---

# B. Should the dataset contain the complete original webpage, or only audit features?

## Answer

It should contain **both**, but not by duplicating an entire website into every row.

Audit features are lossy aggregate measurements. They can tell a model that a site has a certain word count or trust-signal score, but they cannot teach the model how to rewrite a passage, preserve facts, maintain structure, or generate a specific optimized page. Fine-tuning a text generator requires the actual source text relevant to the target.

The scientifically preferable design is:

1. Store an immutable, content-addressed **website snapshot** once:
   - raw response body/HTML;
   - normalized/rendered text;
   - URL, canonical URL, status, headers, content type, encoding;
   - crawl time, crawler version, render mode, and content hash;
   - page structure needed to reconstruct headings/sections/links.
2. Store each sample's exact **selected source page or passage** (or immutable artifact ID and hash).
3. Store the audit feature vector as a separate versioned representation linked to that snapshot.
4. Store the scope mapping that identifies which site/page/passage each feature describes.

For a rewriting SFT task, the minimum actual text is the source document/passage given to the teacher. For reproducibility, the full website snapshot manifest should also be retained because the site-level audit features describe more than that passage.

Only storing features would make the dataset suitable for a tabular predictor, not a generative student model. Only storing raw webpages would lose the structured context and make scientific comparisons harder. Both layers are needed.

Storage should use deduplicated object storage rather than repeated JSON fields. Samples should carry stable artifact IDs, SHA-256 hashes, byte lengths, MIME types, normalization versions, and passage offsets.

---

# C. Should rewritten content be stored? If yes, what format?

## Answer

**Yes. It is a mandatory target artifact for a rewrite-oriented student.**

The current upstream experiment database stores `modified_document_text`, but the Teacher sample/export does not snapshot it. Relying on a foreign key to an operational table is not sufficient for a portable or publication-grade dataset.

## Recommended representation

Preserve all of the following:

1. **Exact raw teacher output**
   - UTF-8 bytes or lossless text;
   - no silent trimming or Markdown stripping;
   - content hash and byte length.
2. **Exact normalized rewritten document**
   - the content actually injected into the Princeton experiment;
   - normalization pipeline/version;
   - normalized-content hash.
3. **Structured transformation**
   - source artifact ID;
   - target artifact ID;
   - strategy;
   - unified diff or structured span edits where feasible;
   - section/passage offsets;
   - changed/added/deleted token and character counts.
4. **Model-neutral training view**
   - `messages[]` or `instruction`, `input`, `output` generated from the immutable artifacts;
   - training-view schema and renderer version;
   - rendered-view hash.

The authoritative artifact should be exact text, not only a diff. Diffs are valuable for analysis but can become unrecoverable if the source artifact is missing or normalization changes.

The dataset must distinguish:

- raw rewrite-model response;
- parsed/cleaned rewrite used by the experiment;
- downstream generative-engine answer produced after inserting that rewrite.

These are three different artifacts and should never share a generic `response` field.

---

# D. Should the Teacher's complete response be preserved, or only metric deltas?

## Answer

Preserve the **complete response and the metrics**.

Metric deltas are derived labels. They are insufficient to:

- train a text generator;
- recompute metrics under a corrected evaluator;
- audit hallucinations, citations, tone, or safety;
- analyze evaluator failure;
- compare alternative tokenizers or parsers;
- verify that a metric corresponds to the claimed response;
- create future preference pairs;
- reproduce figures or error analyses.

For each baseline and optimized arm, preserve:

- raw provider response body/payload where permitted;
- extracted assistant text;
- finish reason/status;
- citations/tool calls/structured fields returned by the provider;
- request ID and provider response ID;
- usage counts and latency;
- exact prompt messages;
- parsing/normalization version;
- response and normalized-text hashes;
- all evaluator inputs, outputs, and errors.

Keep original metrics, optimized metrics, and deltas as derived columns for efficient analysis. The raw artifacts are the evidence; the metrics are a versioned interpretation of that evidence.

---

# E. Is provenance sufficient for scientific publication?

## Answer

**No.** The current provenance is a promising index, but it is not publication-sufficient.

## What is currently captured well

- source database IDs;
- audit completion time/base URL and a constant audit version label;
- experiment dataset name/version, random seed, temperature, completion time;
- query text/seed/selected rank;
- selected-document URL/title/rank/content hash;
- run IDs, strategy, sample index, provider/model;
- prompt-version ID/string;
- generation-parameter JSON;
- prompt/response hashes;
- evaluator name/version strings;
- run timestamps;
- feature and metric schema labels;
- canonical provenance hash.

## Missing publication provenance

### Executable software environment

- Git repository URL and commit SHA;
- dirty-worktree state or source archive hash;
- exact experiment, audit, Teacher Pipeline, rewrite, retrieval, and evaluator code versions;
- container image digest;
- operating system, architecture, Python version, dependency lockfile hash;
- critical library versions, especially tokenization/NLTK/parsing libraries;
- database schema/Alembic revision;
- worker build/version.

### Model and provider identity

- immutable provider model snapshot/version, not merely a mutable alias;
- model release/checkpoint date or digest when available;
- API endpoint/region/version;
- provider request and response IDs;
- exact request payload and raw response payload;
- safety settings, system defaults, seed support/effective seed;
- top-p, maximum tokens, stop sequences, penalties, tools, response format, and all omitted/default parameters;
- retry count, retry-modified prompt, cache hit/miss, and cache artifact hash.

The current `teacher_model_version` simply repeats `teacher_model`, so it is not an independent version identifier.

### Retrieval and source corpus

- search provider and API version;
- exact search request, locale, market, time, filters, and result ordering;
- complete Top-5 documents, not only selected-document metadata/hash;
- raw and cleaned content for each document;
- crawl/retrieval timestamps and failures;
- document cleaning/versioning procedure;
- source licenses and redistribution permissions.

### Prompt and transformation evidence

- complete system/user prompts rather than hashes;
- prompt-template content and checksum;
- exact original document and parsed rewrite;
- rewrite model identity and parameters (which may differ from the answer-generation model);
- parser/post-processing version;
- all truncation and retry transformations;
- strategy implementation/code checksum.

### Evaluation evidence

- full evaluator configuration and source-code checksum;
- raw evaluator details JSON;
- exact evaluator input text;
- tokenizer/sentence segmenter/version and downloaded resource hash;
- metric definitions, units, aggregation policy, missing-value policy, and precision;
- subjective judge prompts, model, raw responses, calibration data, and adjudication;
- confidence intervals and repeated-run membership.

### Dataset construction

- inclusion/exclusion policy and version;
- persisted skip records and reasons;
- dataset-builder code/config hash;
- complete schema document;
- ordered sample IDs **and sample/provenance hashes** in the manifest;
- split manifests and leakage policy;
- deduplication procedure;
- quality/safety/rights audit;
- known limitations and datasheet/model-card-style documentation.

### Publication operations

- immutable artifact repository/DOI or archival location;
- cryptographic signatures or signed checksums;
- data access date;
- retention guarantees;
- hardware and total cost/usage records if conclusions depend on them.

---

# F. Can this dataset reproduce an experiment two years later?

## Answer

**No—not independently, and not exactly.**

It can identify many operational rows that were involved, assuming the same database still exists and none of the restricted source records was removed outside the ORM. It cannot reconstruct the experiment from the exported dataset alone.

## Missing information

- complete selected source text and all other retrieved documents;
- exact rewritten content;
- exact prompts and raw responses;
- immutable model checkpoints or provider snapshot identifiers;
- exact search index state and provider results;
- code commit/container/dependency environment;
- rewrite cache contents and cache-hit state;
- retry history and prompt truncation history;
- evaluator raw details and runtime resources;
- audit extractor/scorer implementation version and the webpage snapshot used to produce features;
- exact raw website content and crawl configuration;
- full parameter set, including implicit provider defaults;
- persisted skip/error events and worker configuration.

Even with all those fields, a new call to a hosted LLM or live search service may not return byte-identical output two years later. Scientific design should distinguish:

1. **Artifact replay:** recompute evaluations from preserved exact inputs/outputs. This should be achievable.
2. **Pipeline reproduction:** run the same code/model artifacts locally and compare within declared tolerances. This may be achievable when weights are available.
3. **External-service rerun:** call a hosted service again. This can be methodologically comparable but cannot guarantee exact output.

The current dataset does not fully support even artifact replay because the required text artifacts are absent from the export.

---

# G. Can another researcher reproduce one Training Sample exactly?

## Answer

**No.**

Another researcher can verify internal JSON hashes only if they first obtain the missing original artifacts from the operational database or another source. The JSONL record by itself does not contain the bytes needed to verify the document, prompt, or response hashes.

The researcher also cannot reproduce the feature vector implementation from `audit_version="website-audit-schema-v1"` because that label does not resolve to a source commit, container, or extractor configuration. The feature vector is recomputed by the worker using whatever audit-profile code is installed when collection occurs, not necessarily the code that ran when the audit was created.

Similarly, evaluator version strings do not capture the evaluator implementation, dependency behavior, or tokenization resources. A model alias such as an API model name does not guarantee the same underlying hosted model two years later.

What can be reproduced today is limited to:

- parsing the stored sample JSON;
- checking its `provenance_hash` against its stored provenance object;
- checking the dataset manifest hash against its manifest;
- observing recorded metric maps and deltas.

That is record-integrity checking, not experimental reproduction.

---

# H. Will future LoRA training require additional information not currently stored?

## Answer

**Yes.** LoRA changes which model parameters are trained, but it does not remove the need for complete SFT examples and a reproducible training specification.

## Missing dataset fields

- canonical input/output or role-based messages;
- exact original and rewritten text;
- exact instructions/prompts;
- target/loss-bearing assistant text;
- loss mask boundaries;
- language/locale;
- split and leakage-group assignments;
- sample weights;
- inclusion/quality/safety/factuality labels;
- content rights/license/consent fields;
- token counts and overlength handling;
- deduplication/near-duplicate group;
- chosen/rejected pairs if preference training is planned.

## Missing base-model specification

- exact base model repository and immutable revision/commit;
- base vs instruct checkpoint choice;
- tokenizer repository and revision;
- tokenizer/chat-template hash;
- special-token map;
- context length;
- model license and acceptable-use version;
- precision/quantization configuration.

## Missing LoRA/QLoRA configuration

- adapter method/version;
- target modules;
- rank `r`;
- alpha;
- dropout;
- bias policy;
- modules-to-save;
- initialization method;
- QLoRA quantization type, bit width, compute dtype, double-quantization flag;
- adapter library/version.

## Missing training-run configuration

- seed(s);
- optimizer and version;
- learning rate and scheduler;
- warmup;
- epochs/max steps;
- batch size, gradient accumulation, clipping;
- sequence length, packing/padding/truncation policy;
- label masking policy;
- mixed precision;
- gradient checkpointing;
- distributed-training configuration;
- checkpoint/evaluation cadence;
- early stopping/model-selection criterion;
- hardware topology and software/container digest.

These values belong in a future training-run manifest, not necessarily in every sample, but the dataset must contain the fields required to deterministically render model-specific training examples.

---

# I. Would the same current schema be sufficient for Qwen, Llama, Mistral, and Gemma?

## Answer

**No.** The current schema is insufficient for all four because it lacks actual SFT inputs and targets.

The long-term research schema should be **model-neutral**, but each training framework needs a versioned adapter:

```text
Immutable semantic sample
  -> Qwen chat-template adapter
  -> Llama chat-template adapter
  -> Mistral chat-template adapter
  -> Gemma chat-template adapter
  -> tokenizer-specific input_ids / attention_mask / labels
```

Qwen documents message-based SFT records; Mistral's documented SFT format is also a `messages` list and computes loss on assistant messages; Llama recipes accept custom preprocessing that must produce model inputs/labels; Gemma describes input/expected-response pairs and supports multiple tuning frameworks. See [Qwen training format](https://qwen.readthedocs.io/en/v1.5/training/SFT/example.html), [Mistral fine-tuning format](https://docs.mistral.ai/resources/deprecated/finetuning/text_vision_finetuning), [Llama dataset preprocessing](https://github.com/meta-llama/llama-cookbook/blob/main/getting-started/finetuning/datasets/README.md), and [Gemma tuning overview](https://ai.google.dev/gemma/docs/tune).

The semantic dataset should therefore store role/content messages or task/instruction/input/target artifacts without embedding any vendor's special tokens. Model-specific adapters should apply the exact tokenizer and chat template at training time and record their revisions and rendered hashes.

The current schema also lacks fields needed to decide whether a sample fits each model's context window, whether it should be truncated, and which tokens receive loss. Thus, even after recovering upstream text, the existing export is not “train once across all models.”

Cross-model comparability additionally requires:

- the same frozen semantic samples and splits;
- model-specific renderers with versioned output hashes;
- equivalent loss masking;
- explicit overlength policy;
- base-model/license compatibility;
- comparable training budgets and evaluation protocols.

---

# J. Teacher Pipeline architecture evaluation

## J.1 Scientific weaknesses

### 1. The learning objective is undefined

The sample combines website features and experiment metrics but does not say whether the student should rewrite content, choose a strategy, predict a metric, or generate the downstream answer. These objectives require different inputs and labels. A dataset must not leave this choice to an undocumented future preprocessing script.

### 2. Critical evidence is referenced, not snapshotted

Foreign keys and hashes point to mutable operational storage. The sample/export is not self-contained. Scientific datasets should contain artifacts or immutable, durable, content-addressed references with retention guarantees.

### 3. The audit and experiment source may be semantically misaligned

The feature vector describes the property's audited website, while a Princeton experiment may optimize a retrieved document from another URL/domain. The sample does not record why site-level features are valid context for that selected document, nor page/passage feature scope. This can create spurious training correlations.

### 4. Audit versioning is nominal rather than executable

`website-audit-schema-v1` is a constant. The worker recomputes features from audit rows using current code. There is no extractor code hash, configuration, or persisted feature-vector creation version. Reprocessing the same audit after a code change could silently produce a different feature vector with the same audit version label.

### 5. Teacher model identity is ambiguous

`teacher_model_version` duplicates `teacher_model`. Hosted aliases can change. The rewrite model and downstream answer-generation model can also differ, but the sample exposes only the optimized experiment run's provider/model as “the teacher.”

### 6. Pairing by `sample_index` is necessary but not a complete experimental block

The pipeline checks query, sample index, provider, and model, but does not explicitly verify:

- identical retrieved document set and order;
- identical selected-document bytes;
- identical prompt template where required;
- identical full generation parameters;
- identical retrieval time/context;
- identical evaluator set;
- strategy-specific rewrite model context.

The provenance may reveal some differences after the fact, but validation should explicitly define the pairing invariant.

### 7. Multiple rows are statistically dependent

Rows from the same property, query, source document, seed, campaign, or experiment are correlated and often near duplicates. Treating them as IID samples would inflate effective sample size and leak into validation/test sets.

### 8. Metric optimization can teach undesirable behavior

Some current rewrite prompts explicitly allow fabricated statistics, quotations, or citations. The evaluator primarily rewards citation visibility/position rather than factual correctness. Training directly on high-delta outputs could teach the student to fabricate authority signals or game the metric.

Before student training, samples require truthfulness, source-entailment, citation-validity, semantic-preservation, and safety gates. Some strategies or samples may need exclusion regardless of visibility gain.

### 9. No negative, neutral, or preference policy

The pipeline includes every valid optimized run, including regressions, but does not specify how negative deltas should be used. SFT on a poor rewrite would still teach that rewrite as the target. A future dataset must distinguish accepted SFT targets from counterexamples, preference rejects, evaluation-only samples, and abstentions.

### 10. Metrics lack uncertainty and aggregation context

Each row stores point metrics/deltas but not confidence intervals, repeated-run variance, paired-test results, effect-size uncertainty, or multiple-comparison controls. One stochastic run should not be treated as a reliable teacher label.

### 11. Skips are not durable research records

Skip reasons are returned in worker memory and then lost. This prevents analysis of selection bias and makes dataset construction irreproducible.

## J.2 Dataset/versioning weaknesses

### 12. Manifest integrity is incomplete

The manifest hashes a list of sample IDs and summary strings, not sample content/provenance hashes, schema artifacts, or export bytes. A sample record altered outside ORM protection could leave the manifest apparently valid.

### 13. Immutability is application-level, not database-enforced

SQLAlchemy listeners reject normal ORM update/delete operations, but direct SQL, bulk operations, privileged administrators, backups/restores, or another application can bypass them. Publication-grade immutability needs append-only permissions, audit logging, signed manifests, and/or immutable object storage.

### 14. Dataset version allocation is race-prone

`count() + 1` is not concurrency-safe. Two workers can choose the same version. There is no database lock, sequence-based version allocator, job lease, or idempotency key for the append transaction.

### 15. Cumulative membership scales quadratically

Every append loads every prior sample and inserts membership for all samples again. Over many versions, membership rows grow approximately with the sum of all historical dataset sizes. This becomes expensive for large, continuously growing datasets.

### 16. JSON blobs lack schema enforcement

Feature vectors, metrics, and provenance are `Text`. The database cannot validate types, required keys, schema versions, numeric finiteness, or feature compatibility. String labels alone do not ensure schema stability.

### 17. Only the latest dataset is exportable

The API does not export a requested historical dataset version. Publication claims must be able to retrieve the exact cited version, not whichever version is latest.

### 18. Export format is research metadata, not training data

The JSONL mixes a dataset-metadata record with sample records. That is reasonable for archival exchange but generally needs a separate manifest and samples file for training frameworks. There is no schema/content-type version in the HTTP contract or export checksum.

### 19. No split, quality, or dataset-card artifacts

There are no frozen split memberships, quality summaries, distribution statistics, known limitations, rights inventory, or slice analysis.

## J.3 Long-term scalability weaknesses

### 20. Full-table polling and loading

Each cycle loads all completed experiments with queries, documents, runs, prompts, evaluations, and metrics, and loads all processed run IDs. Cost grows with the complete history rather than new work.

### 21. No durable job state or leasing

The worker is a single polling loop with no job table, cursor, lease, heartbeat, retry classification, dead-letter queue, cancellation, or persisted failure count. Multiple workers can race.

### 22. One large transaction per append

A large batch adds all new samples, a cumulative dataset, and all membership rows in one transaction. A single conflict can roll back the batch, and there is no checkpointing.

### 23. Large text would stress PostgreSQL if added naïvely

The missing artifacts should not all be copied into every sample row. Content-addressed object storage, compression, deduplication, lifecycle policies, and artifact manifests are required.

### 24. No data drift or coverage monitoring

There is no monitoring for provider/model changes, strategy distribution, language/domain imbalance, missing features, label drift, duplicate rate, factuality failures, or audit/experiment alignment.

## J.4 Enterprise-readiness weaknesses

### 25. Tenant isolation and authorization are insufficient

The read API relies on optional `property_id` filtering, while the dataset export is global and has no visible authorization layer. In a multi-tenant system, this can expose one customer's website-derived data to another.

### 26. Rights, privacy, and governance are absent

Webpage and model-response data can contain copyrighted text, personal data, confidential content, or secrets. There is no data classification, DLP/PII scan, license basis, consent record, regional residency, retention schedule, deletion workflow, or legal hold.

### 27. Security controls are absent from the dataset layer

There is no documented encryption-key scope, signed export, access audit, service identity, least-privilege role, artifact malware/content scanning, or secret redaction.

### 28. Operational observability is minimal

The worker logs to stdout. There are no metrics/SLOs for backlog age, processing latency, skip rate, version failures, duplicates, or export access. The UI's `ready` state only means at least one sample exists, not that the dataset passed scientific quality gates.

### 29. No disaster-recovery or archival guarantees

Foreign-key restrictions protect normal deletes but do not define backup validation, point-in-time recovery, archive replication, checksum verification, or long-term artifact availability.

### 30. No release/promotion process

Every successful append becomes the latest dataset. There is no distinction between draft, quarantined, validated, publication candidate, approved, deprecated, or revoked datasets.

---

## Recommended improvements, without implementation

### Priority 0 — Decide the learning problem

Choose and version one or more explicit training views:

1. **Rewrite SFT:** instruction + original content + features -> validated rewritten content.
2. **Strategy selection/classification:** content + features -> strategy/abstain.
3. **Impact regression/ranking:** baseline/candidate features -> metric distribution or pairwise rank.
4. **Answer generation:** query + retrieved documents -> teacher answer.

Do not combine them into one ambiguous target. A single evidence record may generate multiple versioned training views.

### Priority 1 — Preserve the complete evidence bundle

Introduce immutable content-addressed artifacts for:

- website snapshot and relevant page/passage;
- all retrieved documents;
- original and rewritten documents;
- raw and normalized rewrite outputs;
- exact request messages and provider responses for both arms;
- evaluator details and outputs;
- prompt templates;
- code/config/environment manifests.

Reference each artifact by stable ID, SHA-256, media type, byte length, storage URI, creation time, and retention class.

### Priority 2 — Establish scientific acceptance gates

Before a run becomes an SFT target, require:

- source/rewrite semantic preservation;
- factual entailment and fabricated-claim detection;
- citation resolution/validity;
- safety/policy screening;
- minimum repeated-run evidence or uncertainty threshold;
- explicit treatment of negative/neutral deltas;
- documented human/teacher adjudication for ambiguous cases.

Quarantine known fabricated-statistic/quotation/citation strategies unless the research objective explicitly studies them and they are never used as accepted truthfulness targets.

### Priority 3 — Build publication-grade dataset releases

Each version should freeze:

- exact sample and artifact hashes;
- semantic schema and training-view renderer versions;
- inclusion/exclusion and skip logs;
- group-aware train/validation/test splits;
- deduplication clusters;
- quality/safety/rights reports;
- descriptive statistics and slice coverage;
- signed manifest and complete export checksum;
- dataset card and known limitations;
- immutable historical download endpoint.

### Priority 4 — Make collection durable and scalable

Use event/outbox-driven processing or cursor-based durable jobs with leases, heartbeats, idempotency, retries, and dead-letter records. Allocate versions transactionally. Use incremental/parent manifests rather than copying cumulative membership on every append, while still allowing a version to resolve to an exact full snapshot.

### Priority 5 — Add enterprise governance

Add organization/property ownership, role-based access, tenant-scoped exports, encryption, access logs, data classification, licensing/consent records, regional storage policy, retention/deletion/legal-hold workflows, backup verification, and dataset release approval.

---

## Proposed minimum publication-grade sample contract

The following is a design target, not an implementation request:

```text
identity
  sample_id
  semantic_schema_version
  training_view_version
  created_at

lineage
  organization_id / property_id
  audit_id + immutable audit artifact
  experiment/query/run IDs
  baseline_run_id / treatment_run_id
  campaign and leakage-group IDs

task
  task_type
  instruction
  input artifact references
  canonical messages
  assistant target artifact
  loss-mask policy

content
  website snapshot manifest
  selected source document text/artifact
  original content
  raw rewrite response
  normalized rewritten content
  baseline answer
  optimized answer
  complete prompts and raw provider payloads

features and labels
  audit feature vector + extractor version/hash
  baseline/treatment feature vectors and deltas
  original/optimized metrics and deltas
  uncertainty/repeat statistics
  factuality, preservation, citation-validity, safety labels
  acceptance/preference decision

teacher provenance
  provider, immutable model identifier
  rewrite model and answer model separately
  full generation parameters/defaults
  request/response IDs
  prompt/evaluator/retrieval versions and code hashes
  cache/retry/truncation history

dataset governance
  source license and permitted use
  PII/data classification
  inclusion/exclusion reason
  quality score
  split and group assignment
  deduplication cluster
  sample weight

integrity
  hashes for every artifact
  canonical record hash
  signed dataset manifest membership
```

---

## Final answers at a glance

| Question | Conclusion |
|---|---|
| A. Direct Qwen/Llama SFT? | **No.** No explicit task, actual input, target, messages, source/rewrite text, split, or quality/governance fields. |
| B. Full webpage or features? | **Both.** Deduplicated immutable website/page artifacts plus versioned structured features. |
| C. Store rewritten content? | **Yes.** Raw output, normalized experiment input, exact target text, hashes, and structured diff. |
| D. Preserve full teacher response? | **Yes.** Preserve full raw/normalized responses and keep metrics/deltas as derived labels. |
| E. Publication provenance sufficient? | **No.** Missing artifacts, code/environment, immutable model IDs, full requests, retrieval state, evaluator internals, construction policy, and rights. |
| F. Reproduce in two years? | **No.** Current export cannot replay artifacts or recreate external service state. |
| G. Reproduce one sample exactly? | **No.** It supports record-integrity checking, not independent experimental reconstruction. |
| H. LoRA-ready? | **No.** Missing SFT records, splits/masks/quality plus base-model, tokenizer, adapter, and training manifests. |
| I. Same schema for four model families? | **Not currently.** Use a complete model-neutral semantic schema plus versioned model-specific rendering/tokenization adapters. |
| J. Architecture assessment | Strong foundation for IDs, pairing, and hashes; weak on actual artifacts, objective definition, scientific controls, scaling, concurrency, tenancy, and governance. |

## Final recommendation

Do not begin Qwen/Llama/Mistral/Gemma fine-tuning from the current JSONL export. First define the student task, preserve the full evidence bundle, add truthfulness and semantic-preservation gates, create leakage-safe frozen splits, and release a signed publication-grade dataset version. Until then, treat Teacher Pipeline output as **experiment evidence metadata**, not supervised training data.
