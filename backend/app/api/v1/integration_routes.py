"""Authenticated property handoff and owner-consented GEO research integration."""

import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Query
from app.core.database import SessionLocal
from app.integration.adapter import GeoResearchIntegrationAdapter
from app.integration.research_pipeline import ResearchPipelineBlocked, run_owner_research_pipeline
from app.ge.search_provider import SearchProviderError
from app.experiment.new_website_validation import NewWebsiteValidationError
from app.core.config import settings

router = APIRouter(prefix="/api/v1/integration", tags=["Integration"])

OWNER_RESEARCH_TARGETS = {
    "geoairesume-owner-test-v1": {
        "hostname": "geo-ai-resume.vercel.app",
        "property_id": 2,
        "audit_id": 7,
        "opportunity_id": 3,
    },
    "whisker-haven-owner-demo-20261023-v1": {
        "hostname": "whisker-haven-demo.vercel.app",
        "property_id": 3,
        "audit_id": 6,
        "opportunity_id": 1,
    },
}


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
    return matches[-1]


@router.post("/research-run")
async def run_controlled_research(
    profile: dict,
    authorization: str | None = Header(default=None),
    handoff_token: str | None = Header(default=None, alias="X-GEO-Engine-Handoff-Token"),
):
    """Run live GEO research for one of the exact handed-off owner fixtures."""
    if not _authorized(authorization, handoff_token):
        raise HTTPException(status_code=401, detail="authenticated research token required")
    if profile.get("profile_type") != "owner_controlled_test" or profile.get("controlled_fixture") is True:
        raise HTTPException(status_code=403, detail="an owner-controlled profile without fixture mode is required")
    if str(os.environ.get("APP_ENV", "")).lower() not in {"test", "staging", "development"}:
        raise HTTPException(status_code=403, detail="owner research execution is not enabled in production")
    target = OWNER_RESEARCH_TARGETS.get(str(profile.get("profile_id") or ""))
    identity = profile.get("identity") or {}
    from urllib.parse import urlparse
    hostname = (urlparse(str(identity.get("website") or "")).hostname or "").lower()
    if not target or hostname != target["hostname"]:
        raise HTTPException(status_code=403, detail="profile is outside the owner-research allowlist")
    if int(profile.get("property_id") or 0) != target["property_id"]:
        raise HTTPException(status_code=403, detail="handed-off GEO property does not match the owner-research allowlist")
    if int(profile.get("audit_id") or 0) != target["audit_id"] or int(profile.get("opportunity_id") or 0) != target["opportunity_id"]:
        raise HTTPException(status_code=403, detail="Audit and Opportunity must match the verified owner fixture records")
    if str((profile.get("consent") or {}).get("status") or "").upper() != "VERIFIED":
        raise HTTPException(status_code=403, detail="verified owner consent is required")
    store_root = os.environ.get("GEO_ENGINE_INTEGRATION_STORE", ".integration-data")
    try:
        with SessionLocal() as db:
            return run_owner_research_pipeline(
                db,
                profile=profile,
                store_root=store_root,
                audit_id=target["audit_id"],
                opportunity_id=target["opportunity_id"],
            )
    except ResearchPipelineBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (NewWebsiteValidationError, SearchProviderError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
