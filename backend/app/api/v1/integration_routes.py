"""Authenticated, registration-only integration endpoint.

This endpoint deliberately calls only ``GeoResearchIntegrationAdapter.import_profile``.
It never starts audits, experiments, citation tests, deployments, or monitoring.
"""

import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Query
from app.core.database import SessionLocal
from app.integration.adapter import GeoResearchIntegrationAdapter
from app.integration.research_pipeline import ResearchPipelineBlocked, run_research_pipeline

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
    return matches[-1]


@router.post("/research-run")
async def run_controlled_research(
    profile: dict,
    authorization: str | None = Header(default=None),
    handoff_token: str | None = Header(default=None, alias="X-GEO-Engine-Handoff-Token"),
):
    """Run the existing controlled fixture pipeline for an owner-approved site.

    This route is intentionally authenticated and requires an explicit
    ``controlled_fixture`` flag.  It does not accept provider credentials,
    start paid evaluations, deploy content, or enable monitoring.  The route
    exists so a staging acceptance runner can exercise the same persisted GEO
    Engine pipeline used by local integration tests.
    """
    if not _authorized(authorization, handoff_token):
        raise HTTPException(status_code=401, detail="authenticated research token required")
    if profile.get("profile_type") != "owner_controlled_test" or profile.get("controlled_fixture") is not True:
        raise HTTPException(status_code=403, detail="controlled fixture execution required")
    if str(os.environ.get("APP_ENV", "")).lower() not in {"test", "staging", "development"}:
        raise HTTPException(status_code=403, detail="controlled research route is not enabled in production")
    profile.pop("controlled_fixture", None)
    store_root = os.environ.get("GEO_ENGINE_INTEGRATION_STORE", ".integration-data")
    try:
        with SessionLocal() as db:
            return run_research_pipeline(
                db,
                profile=profile,
                store_root=store_root,
                allow_controlled_fixture=True,
            )
    except ResearchPipelineBlocked as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
