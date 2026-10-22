"""Authenticated, registration-only integration endpoint.

This endpoint deliberately calls only ``GeoResearchIntegrationAdapter.import_profile``.
It never starts audits, experiments, citation tests, deployments, or monitoring.
"""

import hmac
import os

from fastapi import APIRouter, Header, HTTPException
from app.core.database import SessionLocal
from app.integration.adapter import GeoResearchIntegrationAdapter

router = APIRouter(prefix="/api/v1/integration", tags=["Integration"])


def _authorized(authorization: str | None) -> bool:
    expected = os.environ.get("GEO_ENGINE_HANDOFF_TOKEN", "")
    supplied = authorization or ""
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    return bool(expected) and hmac.compare_digest(supplied, expected)


@router.get("/health")
async def integration_health():
    return {"status": "ready", "scope": "property_registration_only"}


@router.post("/profile-import")
async def import_profile(profile: dict, authorization: str | None = Header(default=None)):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="authenticated handoff token required")
    store_root = os.environ.get("GEO_ENGINE_INTEGRATION_STORE", ".integration-data")
    with SessionLocal() as db:
        return GeoResearchIntegrationAdapter(db, store_root).import_profile(profile)
