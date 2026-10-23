"""Authenticated, registration-only integration endpoint.

This endpoint deliberately calls only ``GeoResearchIntegrationAdapter.import_profile``.
It never starts audits, experiments, citation tests, deployments, or monitoring.
"""

import hmac
import os

from fastapi import APIRouter, Header, HTTPException, Query
from app.core.database import SessionLocal
from app.integration.adapter import GeoResearchIntegrationAdapter

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
