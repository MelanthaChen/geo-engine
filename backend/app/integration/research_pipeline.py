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
