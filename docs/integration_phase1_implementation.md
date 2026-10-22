# GEO research integration — Phase 1 implementation

Phase 1 adds a local, versioned adapter around existing GEO Engine records. It does not replace or alter Property, Website Audit, Experiment Lab, Citation Tests, or immutable Teacher records.

## Contract and files

The shared contract is `geo-research-integration/v1`. JSON Schemas are in [`schemas/geo-research-integration/v1`](/Users/melc/Documents/Intern/LLM%20Search%20Optimizer/geo-engine/schemas/geo-research-integration/v1):

- `profile_import.schema.json`
- `property_identity_mapping.schema.json`
- `audit_result_reference.schema.json`
- `ranked_strategy_recommendation.schema.json`
- `exact_text_edit_proposal.schema.json`
- `evaluation_question_set.schema.json`
- `baseline_experiment_reference.schema.json`
- `deployment_receipt.schema.json`
- `post_deployment_evaluation.schema.json`
- `research_result_export.schema.json`

The adapter accepts the existing Outreach Agent `geo-company-profile/v1` export and preserves the original payload, source profile ID, source profile version, source schema version, timestamp, and provenance. Import is consent-gated: `consent.status` must be `VERIFIED`, with a consent ID, version, research scope, and non-expired validity. Contact discovery, positive screening, or outreach readiness never substitutes for consent. The normalized profile types are `business_company`, `hotel_property`, and `owner_controlled_test`.

## Adapter entry points and commands

Python entry points:

- `app.integration.contracts.normalize_profile_import()` and `validate_record()`
- `app.integration.adapter.GeoResearchIntegrationAdapter.import_profile()`
- `app.integration.adapter.GeoResearchIntegrationAdapter.run_read_only_audit()`
- `app.integration.adapter.GeoResearchIntegrationAdapter.record_deployment()`

CLI, run from the repository root:

```sh
PYTHONPATH=backend python3 backend/scripts/geo_research_integration.py import-profile path/to/profile.json --store .integration-data
PYTHONPATH=backend python3 backend/scripts/geo_research_integration.py audit path/to/normalized-profile.json --store .integration-data
```

`import-profile` only normalizes and writes local JSONL records. `audit` invokes the existing Website Audit service and therefore may crawl the official URL; it does not call an LLM, retrieve paid search results, publish content, or deploy anything. The adapter writes append-only files under the selected store directory: `profile_import.jsonl`, `property_identity_mapping.jsonl`, `audit_result_reference.jsonl`, and `deployment_receipt.jsonl`.

Property IDs remain GEO Engine-owned. A matching domain reuses the existing Property; the canonical owner-test URL is `https://geo-ai-resume.vercel.app`. Owner-controlled tests are excluded from formal cohorts. A second hotel profile sharing a chain domain is rejected unless a future explicit property mapping is supplied; it is never silently merged by domain.

`GeoResearchIntegrationAdapter.create_question_sets()` creates separate deterministic `fixed-v1` and `dynamic-v1` pools. They have distinct IDs and must not be aggregated as one comparable question set. `create_monitoring_plan()` keeps monitoring paused unless verified implementation evidence exists, and `MonitoringPlan.authorize_run()` enforces verified consent, active status, and per-company/global budgets before any future provider runner is called. Provider calls are not implemented or automatically triggered in Phase 1.

## Safety and evidence boundaries

Audit results reference existing audit/page IDs, page URLs, evidence hashes, and failure states. Missing evidence remains null/empty and is not inferred. Strategy ranking is deliberately represented as `rule_based_existing_recommendations` and is limited to three entries; no ML ranker is introduced. Experiment and citation references are reference-only and must be created from real existing IDs/statuses; `results_present: false` is valid for not-run baselines/post results.

Deployment receipts are persistent append-only records and duplicate receipt IDs are replay-safe. Phase 1 does not publish, call Vercel, modify another repository, send outreach, run provider-backed experiments, or create automatic deployment callbacks. Approval, stale, rejected, not-deployed, and failed states remain explicit.

## Tests and remaining blockers

`backend/tests/test_geo_research_integration.py` covers schema validation, import idempotency, Property reuse, hotel identity protection, owner-test exclusion, missing audit evidence, rejected/stale proposals, no fabricated baseline/post results, and duplicate deployment receipt handling.

Remaining Phase 1/next-phase blockers are authenticated service-to-service transport, tenant/ownership authorization, an explicit mapping resource for distinct hotel properties that share a domain, a read-only strategy/result API, owner-provided deployment receipts, and a first-class post-deployment relation. Automatic publishing and post-deployment evaluation remain intentionally out of scope.

## Contract decisions requested from sibling repositories

1. Continue emitting `geo-company-profile/v1` with stable `profile_id` and immutable profile version/hash.
2. Emit a distinct hotel property `profile_id` for every property, even when chain domains match.
3. Mark GeoAIResume as `owner_controlled_test` with no formal cohort membership and use `https://geo-ai-resume.vercel.app`.
4. Treat contact evidence as provenance only; do not send contact PII for audit integration.
5. Provide real deployment receipt fields only after owner approval and deployment; do not use publishing-job IDs as deployment IDs.
