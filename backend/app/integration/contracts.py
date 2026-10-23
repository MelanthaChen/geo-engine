from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import hashlib
import json
from datetime import datetime

from jsonschema import Draft202012Validator


CONTRACT_VERSION = "geo-research-integration/v1"
PROFILE_SCHEMA_VERSION = "geo-company-profile/v1"
CANONICAL_GEOAIRESUME_URL = "https://geo-ai-resume.vercel.app"
SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas" / "geo-research-integration" / "v1"


class ConsentError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _domain(url: str) -> str:
    value = url.strip()
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    return (parsed.hostname or "").lower().rstrip(".")


def _first(data: dict[str, Any], *paths: tuple[str, ...], default=None):
    for path in paths:
        value: Any = data
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value not in (None, ""):
            return value
    return default


def normalize_profile_import(source: dict[str, Any], received_at: str | None = None) -> dict[str, Any]:
    """Adapt geo-company-profile/v1 without changing the source payload."""
    identity = source.get("identity") or {}
    profile_type = source.get("profile_type")
    if profile_type in {"hotel_property", "hotel", "HOTEL_PROPERTY"}:
        entity_type = "hotel_property"
    elif profile_type in {"owner_controlled_test", "OWNER_CONTROLLED_TEST"}:
        entity_type = "owner_controlled_test"
    else:
        entity_type = "business_company"

    source_profile_id = source.get("profile_id") or source.get("source_profile_id")
    official_name = _first(source, ("official_name",), ("name",), ("identity", "name"), default=source_profile_id)
    official_url = _first(source, ("official_domain",), ("official_url",), ("identity", "website_url"), ("identity", "website"), default=None)
    if not source_profile_id or not official_name or not official_url:
        raise ValueError("profile_id, identity.name, and identity.website_url are required")
    consent = source.get("consent") or source.get("research_consent") or {}
    if not isinstance(consent, dict):
        raise ConsentError("research consent must be an object")
    consent_status = str(consent.get("status", "")).upper()
    if consent_status != "VERIFIED":
        raise ConsentError("research consent must be VERIFIED; contact discovery and screening are not consent")
    if not consent.get("consent_id") or not consent.get("version"):
        raise ConsentError("verified consent requires consent_id and version")
    if not consent.get("research_scope"):
        raise ConsentError("verified consent requires research_scope")
    valid_until = consent.get("valid_until")
    if valid_until and datetime.fromisoformat(str(valid_until).replace("Z", "+00:00")) <= datetime.now(timezone.utc):
        raise ConsentError("research consent is expired")
    # Owner-controlled fixtures may represent different isolated demo sites.
    # Preserve the supplied URL so one fixture cannot be silently mapped to
    # another fixture's Property. GeoAIResume remains unchanged when supplied
    # as the source URL.
    canonical_url = official_url.rstrip("/")
    classifications = source.get("classifications") or []
    cohort = source.get("cohort_membership") or source.get("cohort_memberships") or {}
    if isinstance(cohort, dict):
        cohorts = [name.upper() + "_COHORT" for name, enabled in cohort.items() if enabled and name.lower() in {"smb", "hotel"}]
    else:
        cohorts = list(cohort)
    if entity_type == "owner_controlled_test":
        cohorts = []
    return {
        "contract_version": CONTRACT_VERSION,
        "record_type": "profile_import",
        "schema_version": CONTRACT_VERSION,
        "record_id": f"profile-import:{source_profile_id}:{source.get('source_profile_version') or source.get('profile_version') or sha256_json(source)}",
        "source_system": "geo-research-outreach-agent",
        "source_schema_version": source.get("schema_version", PROFILE_SCHEMA_VERSION),
        "source_profile_id": str(source_profile_id),
        "source_profile_version": str(source.get("source_profile_version") or source.get("profile_version") or sha256_json(source)),
        "profile_type": entity_type,
        "cohort_ids": [str(source.get("cohort_id"))] if source.get("cohort_id") else [],
        "formal_cohort_memberships": cohorts,
        "official_name": str(official_name),
        "official_domain": canonical_url,
        "official_urls": source.get("official_urls") or [canonical_url],
        "profile_snapshot": source,
        "consent": consent,
        "received_at": received_at or utc_now(),
        "provenance": {
            "source_system": "geo-research-outreach-agent",
            "source_profile_id": str(source_profile_id),
            "source_schema_version": source.get("schema_version", PROFILE_SCHEMA_VERSION),
            "source_record_hash": sha256_json(source),
            "normalized_domain": _domain(canonical_url),
        },
    }


def validate_record(record_type: str, record: dict[str, Any]) -> None:
    path = SCHEMA_DIR / f"{record_type}.schema.json"
    if not path.exists():
        raise ValueError(f"Unknown integration record type: {record_type}")
    schema = json.loads(path.read_text())
    # Common envelope fields are intentionally extensible across record types;
    # the schemas list the contract-critical fields and preserve extra provenance.
    schema["additionalProperties"] = True
    errors = sorted(Draft202012Validator(schema).iter_errors(record), key=lambda error: list(error.path))
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "$"
        raise ValueError(f"{record_type} schema validation failed at {location}: {errors[0].message}")
