"""Controlled, retry-safe GEO research orchestration.

This coordinator composes existing GEO Engine persistence/services. It does
not enable paid providers, deployments, monitoring, or website changes. A
provider executor and audit runner are injected for local/staging fixtures;
production callers must explicitly provide an approved execution policy.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.integration.adapter import GeoResearchIntegrationAdapter
from app.integration.contracts import utc_now
from app.models.experiment import Experiment
from app.services.website_audit.audit_service import run_website_audit


class ResearchPipelineBlocked(PermissionError):
    pass


def run_research_pipeline(
    db: Session,
    *,
    profile: dict[str, Any],
    store_root: str,
    audit_runner: Callable | None = None,
    provider_executor: Callable[[list[str], list[str]], dict[str, Any]] | None = None,
    allow_controlled_fixture: bool = False,
) -> dict[str, Any]:
    """Run the existing stages and persist a traceable result envelope.

    ``allow_controlled_fixture`` is intentionally explicit. Without it this
    function refuses provider execution, preventing a local staging run from
    silently becoming a paid GEO experiment.
    """
    consent = profile.get("consent") or {}
    if str(consent.get("status", "")).upper() != "VERIFIED":
        raise ResearchPipelineBlocked("research pipeline requires verified consent")
    adapter = GeoResearchIntegrationAdapter(db, store_root)
    imported = adapter.import_profile(profile)
    source_id = imported["source_profile_id"]
    source_version = imported["source_profile_version"]
    existing = next(
        (item for item in adapter.store.records("research_result_export")
         if item.get("source_profile_id") == source_id and item.get("source_profile_version") == source_version),
        None,
    )
    if existing:
        return {"status": "COMPLETED", "idempotent": True, "result": existing}
    if provider_executor is None and not allow_controlled_fixture:
        raise ResearchPipelineBlocked("provider execution requires explicit authorization")

    profile = {**imported, "property_id": imported["property_id"]}
    audit_object: Any = None

    def run_audit(db_session, property_record):
        nonlocal audit_object
        if audit_runner:
            audit_object = audit_runner(db_session, property_record)
        else:
            # Render Free staging does not guarantee a Chromium executable.
            # Controlled fixtures remain bounded and evidence-based through
            # the HTTP-first audit path; production audit policy is unchanged.
            audit_object = run_website_audit(
                db_session,
                property_record,
                browser_fallback_enabled=not allow_controlled_fixture,
            )
        return audit_object

    audit = adapter.run_read_only_audit(profile, audit_runner=run_audit)
    fixed, dynamic = adapter.create_question_sets(profile, website_text=[str(audit.get("website_profile", {}))])
    questions = [item["text"] for item in fixed["questions"] + dynamic["questions"]]
    query_universe = adapter.create_query_universe(profile=profile, questions=questions)
    if audit_object is None:
        raise RuntimeError("audit runner returned no audit object for strategy ranking")
    ranked = adapter.rank_strategies(audit_object, profile)
    if provider_executor is None:
        baseline_results = {"provider": "CONTROLLED_FIXTURE", "queries": query_universe["queries"], "results": []}
    else:
        baseline_results = provider_executor(query_universe["queries"], [item["strategy_id"] for item in ranked["strategies"]])
    experiment = Experiment(
        property_id=profile["property_id"], name=f"Controlled GEO baseline - {profile['official_name']}",
        description="Controlled integration fixture; no paid provider execution.", status="completed",
        provider=str(baseline_results.get("provider", "CONTROLLED_FIXTURE")), llm_model="fixture",
        dataset_name="integration-controlled", benchmark_queries_json=json.dumps(query_universe["queries"]),
        strategies_json=json.dumps([item["strategy_id"] for item in ranked["strategies"]]),
        metrics_json=json.dumps(["fixture_visibility", "fixture_citation_count"]),
        generation_params_json=json.dumps({"controlled_fixture": True}), number_of_queries=len(query_universe["queries"]),
        random_seed=42, temperature=0, total_queries=len(query_universe["queries"]), completed_queries=len(query_universe["queries"]),
        total_samples=1, current_sample=1, visibility_score=0, citation_count=0, pawc=0,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    baseline = adapter.record_baseline(profile=profile, experiment_id=experiment.id, results=baseline_results)
    result = adapter.export_research_result(
        profile=profile, audit_reference=audit, strategies=ranked,
        question_set_reference={"fixed": fixed["record_id"], "dynamic": dynamic["record_id"]},
        baseline_reference=baseline,
    )
    return {
        "status": "COMPLETED", "idempotent": False, "property_id": profile["property_id"],
        "audit": audit, "query_universe": query_universe, "strategies": ranked,
        "baseline": baseline, "result": result,
    }


def run_owner_research_pipeline(
    db: Session,
    *,
    profile: dict[str, Any],
    store_root: str,
    audit_id: int,
    opportunity_id: int,
) -> dict[str, Any]:
    """Run real model research against an existing, consented Audit opportunity.

    The workflow reuses the verified Property, Audit, and Opportunity. Search
    retrieval is live even for the GeoAIResume demo, and answer generation uses
    the configured GEO Engine model provider. This entry point never creates a
    new audit or accepts caller-supplied provider results.
    """
    from sqlalchemy.orm import joinedload

    from app.experiment.experiment_service import ExperimentService
    from app.experiment.new_website_validation import (
        NewWebsiteValidationBuilder,
        NewWebsiteValidationError,
    )
    from app.ge.geo_rewriter import STRATEGY_LABELS
    from app.models.website_audit import WebsiteAudit
    from app.storage.experiment_repository import ExperimentRepository

    consent = profile.get("consent") or {}
    if str(consent.get("status", "")).upper() != "VERIFIED":
        raise ResearchPipelineBlocked("research pipeline requires verified consent")
    adapter = GeoResearchIntegrationAdapter(db, store_root)
    imported = adapter.import_profile(profile)
    if int(imported["property_id"]) != int(profile.get("property_id") or 0):
        raise ResearchPipelineBlocked("consented profile does not map to its handed-off GEO property")
    source_id = imported["source_profile_id"]
    source_version = imported["source_profile_version"]
    existing = next(
        (item for item in adapter.store.records("research_result_export")
         if item.get("source_profile_id") == source_id
         and item.get("source_profile_version") == source_version),
        None,
    )
    if existing:
        baseline = existing.get("baseline") or {}
        if baseline.get("provider") in {None, "CONTROLLED_FIXTURE", "MOCK", "mock"} or int(baseline.get("model_calls") or 0) < 1:
            raise ResearchPipelineBlocked("an existing non-real result is present for this profile; it will not be relabeled as real research")
        return {"status": "COMPLETED", "idempotent": True, "property_id": imported["property_id"], "result": existing}

    audit = (
        db.query(WebsiteAudit)
        .options(
            joinedload(WebsiteAudit.property),
            joinedload(WebsiteAudit.pages),
            joinedload(WebsiteAudit.recommendations),
        )
        .filter(
            WebsiteAudit.id == audit_id,
            WebsiteAudit.property_id == imported["property_id"],
            WebsiteAudit.status == "completed",
        )
        .first()
    )
    if audit is None:
        raise ResearchPipelineBlocked("the specified completed Audit does not belong to this handed-off Property")
    opportunity = next((item for item in audit.recommendations if item.id == opportunity_id), None)
    if opportunity is None:
        raise ResearchPipelineBlocked("the specified Optimization Opportunity does not belong to the completed Audit")

    frozen = NewWebsiteValidationBuilder(db).build(
        property_id=imported["property_id"],
        audit_id=audit_id,
        opportunity_id=opportunity_id,
        use_frozen_demo_pack=False,
    )
    if frozen.get("metadata", {}).get("status") == "content_gap":
        raise NewWebsiteValidationError("live retrieval could not select the audited target page")
    documents = frozen.get("documents") or []
    target = next((item for item in documents if item.get("source_role") == "audited_target"), None)
    if not target or not target.get("content", "").strip() or target.get("retrieval_provider") == "frozen-production-page-snapshot":
        raise ResearchPipelineBlocked("live audited target content was not retrieved")

    evidence_json = opportunity.evidence_json or {}
    strategy = str(evidence_json.get("suggested_strategy") or "faq").strip()
    if strategy not in STRATEGY_LABELS or strategy == "original":
        strategy = "faq"

    repository = ExperimentRepository(db)
    experiment_name = f"Outreach GEO research {source_id} {source_version}"
    prior_experiment = (
        db.query(Experiment)
        .filter(Experiment.property_id == imported["property_id"], Experiment.name == experiment_name)
        .order_by(Experiment.id.desc())
        .first()
    )
    if prior_experiment:
        if prior_experiment.status == "completed" and prior_experiment.run_count:
            experiment = prior_experiment
        elif prior_experiment.status in {"queued", "running"}:
            return {"status": "RUNNING", "property_id": imported["property_id"], "experiment_id": prior_experiment.id, "idempotent": True}
        else:
            raise ResearchPipelineBlocked(
                f"the existing GEO experiment {prior_experiment.id} is {prior_experiment.status}; no duplicate experiment was created"
            )
    else:
        service = ExperimentService(repository=repository)
        experiment = service.create_experiment(
            property_id=imported["property_id"],
            name=experiment_name,
            description=f"Live website research grounded in Audit #{audit_id}, Opportunity #{opportunity_id}.",
            provider="chatgpt",
            llm_model="gpt-3.5-turbo",
            dataset_name="outreach_owner_website_research",
            queries=[frozen["query"]],
            dataset_documents=[{"query": frozen["query"], **document} for document in documents],
            strategies=["original", strategy],
            metrics=["pawc", "citation_count", "visibility_score"],
            number_of_queries=1,
            random_seed=42,
            temperature=0.2,
            repetitions_per_context=1,
        )
        experiment = service.execute_experiment(experiment.id)

    experiment = repository.get_run(experiment.id)
    if not experiment or experiment.status != "completed" or int(experiment.run_count or 0) < 2:
        error = getattr(experiment, "error_message", None) or "GEO experiment did not persist both model strategies"
        raise RuntimeError(error)
    serialized = repository.serialize(experiment)
    query_result = (serialized.get("queryResults") or [{}])[0]
    details = query_result.get("evidence", {}).get("strategyDetails", [])
    if len(details) < 2 or any(not item.get("generatedAnswer") for item in details):
        raise RuntimeError("completed GEO experiment is missing persisted generated model responses")

    model_calls = sum(1 for run in experiment.runs if run.status == "completed")
    if model_calls < 2:
        raise RuntimeError("GEO experiment completed without persisted real model-run records")
    actual_results = [{
        "strategy": item.get("strategy"),
        "response": item.get("generatedAnswer"),
        "metrics": item.get("metrics") or {},
    } for item in details]
    baseline_results = {
        "provider": str(experiment.provider),
        "model": experiment.llm_model,
        "model_calls": model_calls,
        "response_archive": f"experiment:{experiment.id}",
        "results": actual_results,
        "interpretation": "Persisted model-generated answers and GEO Engine evaluations for the original and audit-grounded strategy. These are not third-party AI search rankings.",
    }
    question_sets = adapter.create_question_sets(profile=imported, website_text=[target["content"]])
    ranked = adapter.rank_strategies(audit, imported)
    baseline = adapter.record_baseline(profile=imported, experiment_id=experiment.id, results=baseline_results)
    serialized_pages = [page for page in audit.pages if page.url]
    audit_reference = {
        "contract_version": "geo-research-integration/v1",
        "record_type": "audit_result_reference",
        "schema_version": "geo-research-integration/v1",
        "record_id": f"audit-result:{audit.id}",
        "source_profile_id": source_id,
        "source_profile_version": source_version,
        "property_id": imported["property_id"],
        "audit_id": audit.id,
        "status": audit.status,
        "audit_url": audit.base_url,
        "page_refs": [{
            "page_id": page.id,
            "url": page.url,
            "evidence_hash": page.content_sha256,
            "failure_state": page.extraction_failure_reason,
        } for page in serialized_pages],
        "captured_at": utc_now(),
        "provenance": {"source_system": "geo-engine", "audit_id": audit.id, "property_id": audit.property_id},
    }
    target_strategy = next((item for item in details if item.get("strategy") == strategy), details[-1])
    recommendation = {
        "rank": 1,
        "title": opportunity.title,
        "page_url": target["url"],
        "original_quote": opportunity.observed_evidence or "No exact quote was stored by the Audit.",
        "proposed_revision": target_strategy.get("modifiedDocument") or opportunity.description,
        "rationale": opportunity.why_it_matters or opportunity.description,
        "audit_id": audit.id,
        "opportunity_id": opportunity.id,
        "strategy": strategy,
    }
    research_details = {
        "experiment_id": experiment.id,
        "audit_id": audit.id,
        "opportunity_id": opportunity.id,
        "site": imported["official_domain"],
        "report_title": f"GEO Research Findings - {imported['official_name']}",
        "retrieved_at": frozen.get("metadata", {}).get("retrieved_at"),
        "questions": [frozen["query"]],
        "observed_pages": [{
            "url": target["url"],
            "title": target.get("title") or imported["official_name"],
            "headings": [],
            "exact_quotes": [opportunity.observed_evidence] if opportunity.observed_evidence else [],
            "content_sha256": target.get("content_sha256"),
            "retrieval_provider": target.get("retrieval_provider"),
            "source_audit_id": audit.id,
        }],
        "recommendations": [recommendation],
        "baseline": baseline_results,
        "limitations": [
            "The response archive records GEO Engine model-generated answers from the frozen query and live retrieved documents; it does not measure ranking or citations in external commercial AI search products.",
            "The proposed content revision is a research hypothesis and was not deployed to the website.",
        ],
        "experiment_summary": {
            "experiment_id": experiment.id,
            "status": experiment.status,
            "provider": experiment.provider,
            "model": experiment.llm_model,
            "model_calls": model_calls,
            "retrieval_provider": frozen.get("metadata", {}).get("retrieval_provider"),
            "query": frozen["query"],
        },
    }
    result = adapter.export_research_result(
        profile=imported,
        audit_reference=audit_reference,
        strategies=ranked,
        question_set_reference={"fixed": question_sets[0]["record_id"], "dynamic": question_sets[1]["record_id"]},
        baseline_reference=baseline,
        research_details=research_details,
    )
    return {
        "status": "COMPLETED",
        "idempotent": bool(prior_experiment),
        "property_id": imported["property_id"],
        "experiment_id": experiment.id,
        "audit_id": audit.id,
        "opportunity_id": opportunity.id,
        "result": result,
    }
