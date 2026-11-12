"""Authenticated property handoff and owner-consented GEO research integration."""

import hmac
import os
import hashlib
import re

from fastapi import APIRouter, Header, HTTPException, Query
from app.core.database import SessionLocal
from app.integration.adapter import GeoResearchIntegrationAdapter
from app.integration.research_pipeline import ResearchPipelineBlocked
from app.integration.durable_outreach import submit as submit_durable_job, advance as advance_durable_job
from app.core.config import settings
from app.models.experiment import ExperimentQuery, ExperimentDocument, ExperimentStrategyResult, ExperimentRun


def _enrich_result_sources(record: dict, db) -> dict:
    """Attach hash-verified persisted retrieval provenance to legacy/new exports."""
    result = dict(record)
    experiment_id = (result.get("experiment_summary") or {}).get("experiment_id")
    if experiment_id is not None:
        query = db.query(ExperimentQuery).filter(ExperimentQuery.experiment_id == int(experiment_id)).order_by(ExperimentQuery.id.asc()).first()
        if query:
            strategy_rows = db.query(ExperimentStrategyResult).filter(ExperimentStrategyResult.experiment_query_id == query.id).order_by(ExperimentStrategyResult.strategy.asc()).all()
            run_ids = [row.run_id for row in strategy_rows if row.run_id is not None]
            run_models = {row.id: {"model": row.model, "provider": row.provider, "status": row.status}
                          for row in db.query(ExperimentRun).filter(ExperimentRun.id.in_(run_ids)).all()} if run_ids else {}
            baseline = dict(result.get("baseline") or {})
            archived_results = []
            for strategy in strategy_rows:
                meta = run_models.get(strategy.run_id, {})
                archived_results.append({"strategy": strategy.strategy, "response": strategy.answer,
                    "model": meta.get("model"), "provider": meta.get("provider"),
                    "metrics": {"word_count": strategy.word_count, "citation_count": strategy.citation_count,
                                "visibility_score": strategy.visibility_score, "pawc": strategy.pawc,
                                "position": strategy.position}})
            if archived_results:
                baseline["results"] = archived_results
                baseline["model"] = next((item.get("model") for item in archived_results if item.get("model")), baseline.get("model"))
                baseline["model_calls"] = len(archived_results)
                baseline["interpretation"] = "Persisted model-generated answers and GEO Engine evaluations. These are not third-party AI search rankings."
                result["baseline"] = baseline
            answers = result.get("baseline", {}).get("results", []) or []
            cited = {}
            for answer in answers:
                strategy = str(answer.get("strategy") or "unknown")
                for rank in set(int(value) for value in re.findall(r"\[(\d+)\]", str(answer.get("response") or ""))):
                    cited.setdefault(rank, []).append(strategy)
            sources = []
            for document in db.query(ExperimentDocument).filter(ExperimentDocument.experiment_query_id == query.id).order_by(ExperimentDocument.rank.asc()).all():
                actual_hash = hashlib.sha256((document.plain_text or "").encode("utf-8")).hexdigest()
                stored_hash = document.content_sha256
                if stored_hash and not hmac.compare_digest(actual_hash, stored_hash):
                    raise HTTPException(status_code=409, detail=f"Persisted source integrity mismatch at document rank {document.rank}")
                use = ("Cited in persisted strategy response(s): " + ", ".join(cited.get(document.rank, []))) if cited.get(document.rank) else "Retrieved but not cited in persisted strategy responses"
                if len(document.plain_text or "") < 200:
                    use += "; saved page text is limited, so no substantive finding is attributed to it"
                sources.append({
                    "rank": document.rank, "title": document.title, "url": document.url,
                    "source_type": "target website" if document.source_role == "audited_target" else "external reference",
                    "content_sha256": actual_hash, "retrieval_provider": document.retrieval_provider,
                    "retrieved_at": document.retrieval_timestamp.isoformat() if document.retrieval_timestamp else None,
                    "evidence_id": f"experiment:{experiment_id}:document:{document.rank}", "relevance": use,
                })
            result["research_sources"] = sources
    for recommendation in result.get("recommendations", []) or []:
        proposal = recommendation.get("proposed_revision")
        if not isinstance(proposal, str) or not proposal.strip() or len(proposal.strip()) > 400:
            recommendation["proposed_revision"] = None
        excerpt = recommendation.get("original_quote")
        if isinstance(excerpt, str) and len(excerpt) > 500:
            recommendation["original_quote"] = None
        recommendation.setdefault("supporting_evidence_ids", [
            item["evidence_id"] for item in result.get("research_sources", [])
            if item.get("source_type") == "target website"
        ])
    return result

router = APIRouter(prefix="/api/v1/integration", tags=["Integration"])

def _authorized(authorization: str | None, handoff_token: str | None = None) -> bool:
    expected = os.environ.get("GEO_ENGINE_HANDOFF_TOKEN", "")
    # Authorization is canonical. The explicit integration header is a narrow
    # compatibility path for managed proxies that strip Authorization; it is
    # never a separate credential and is checked against the same secret.
    supplied = authorization or handoff_token or ""
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    return bool(expected) and hmac.compare_digest(supplied, expected)


@router.get("/health")
async def integration_health():
    return {"status": "ready", "scope": "property_registration_only"}


@router.post("/profile-import")
async def import_profile(
    profile: dict,
    authorization: str | None = Header(default=None),
    handoff_token: str | None = Header(default=None, alias="X-GEO-Engine-Handoff-Token"),
):
    if not _authorized(authorization, handoff_token):
        raise HTTPException(status_code=401, detail="authenticated handoff token required")
    store_root = os.environ.get("GEO_ENGINE_INTEGRATION_STORE", ".integration-data")
    with SessionLocal() as db:
        return GeoResearchIntegrationAdapter(db, store_root).import_profile(profile)


@router.get("/research-results/{source_profile_id}")
async def get_research_result(
    source_profile_id: str,
    source_profile_version: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    handoff_token: str | None = Header(default=None, alias="X-GEO-Engine-Handoff-Token"),
):
    """Return the latest persisted result envelope for Outreach retrieval."""
    if not _authorized(authorization, handoff_token):
        raise HTTPException(status_code=401, detail="authenticated result access required")
    store_root = os.environ.get("GEO_ENGINE_INTEGRATION_STORE", ".integration-data")
    with SessionLocal() as db:
        records = GeoResearchIntegrationAdapter(db, store_root).store.records("research_result_export")
    matches = [
        record for record in records
        if record.get("source_profile_id") == source_profile_id
        and (source_profile_version is None or record.get("source_profile_version") == source_profile_version)
    ]
    if not matches:
        raise HTTPException(status_code=404, detail="research result not found")
        return _enrich_result_sources(matches[-1], db)


@router.post("/research-run")
async def run_controlled_research(
    profile: dict,
    authorization: str | None = Header(default=None),
    handoff_token: str | None = Header(default=None, alias="X-GEO-Engine-Handoff-Token"),
):
    """Compatibility endpoint routed through the standard durable job workflow."""
    if not _authorized(authorization, handoff_token):
        raise HTTPException(status_code=401, detail="authenticated research token required")
    key = f"outreach-v2:{profile.get('invitation_id') or ''}"
    allowlist = {item.strip() for item in os.environ.get("GEO_OUTREACH_RESEARCH_JOB_ALLOWLIST", "").split(",") if item.strip()}
    if len(allowlist) != 1 or key not in allowlist:
        raise HTTPException(status_code=403, detail="job is outside the exact configured research allowlist")
    if os.environ.get("GEO_OUTREACH_RESEARCH_ENABLED", "").strip().lower() != "true":
        raise HTTPException(status_code=403, detail="research execution is disabled")
    try:
        with SessionLocal() as db:
            submit_durable_job(db, key, profile)
            return advance_durable_job(db, key)
    except ResearchPipelineBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get('/outreach-capabilities')
def outreach_capabilities(authorization: str | None = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401,detail='authenticated service token required')
    search_provider = settings.SEARCH_PROVIDER
    search_credentials = {
        'exa': bool(settings.EXA_API_KEY),
        'brave': bool(settings.BRAVE_SEARCH_API_KEY),
        'google': bool(settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_ENGINE_ID),
    }.get(search_provider, False)
    model_credentials = bool(settings.OPENAI_API_KEY)
    enabled = os.environ.get('GEO_OUTREACH_RESEARCH_ENABLED', '').lower() == 'true'
    return {
        'contract': 'outreach-durable/v1',
        'durable_jobs': True,
        'research_execution_enabled': enabled,
        'model_provider': 'openai',
        'model_credentials_configured': model_credentials,
        'search_provider': search_provider,
        'search_credentials_configured': search_credentials,
        'provider_connectivity_verified': False,
        'research_ready': enabled and model_credentials and search_credentials,
    }


@router.post('/outreach-jobs')
def create_outreach_job(profile: dict, authorization: str | None = Header(default=None), idempotency_key: str = Header(alias='Idempotency-Key')):
    if not _authorized(authorization):
        raise HTTPException(status_code=401,detail='authenticated service token required')
    from app.integration.durable_outreach import submit
    try:
        with SessionLocal() as db:return submit(db,idempotency_key,profile)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc


@router.get('/outreach-jobs/{job_key:path}')
def read_outreach_job(job_key: str, authorization: str | None = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401,detail='authenticated service token required')
    from app.integration.durable_outreach import get_job
    with SessionLocal() as db:result=get_job(db,job_key)
    if result is None:raise HTTPException(status_code=404,detail='research job not found')
    return result


@router.post('/outreach-advance/{job_key:path}')
def advance_outreach_job(job_key: str, authorization: str | None = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401,detail='authenticated service token required')
    from app.integration.durable_outreach import advance
    with SessionLocal() as db:return advance(db,job_key)
