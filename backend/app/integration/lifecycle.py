from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


LIFECYCLE = (
    "CONSENT_VERIFIED", "PROPERTY_REGISTERED", "WEBSITE_AUDIT", "QUESTION_GENERATION",
    "BASELINE_EVALUATION", "STRATEGY_EXPERIMENTS", "TOP_3_RECOMMENDATIONS", "REPORT_READY",
    "WAITING_FOR_IMPLEMENTATION", "DEPLOYMENT_VERIFIED", "LONG_TERM_MONITORING",
)

# Cross-repository outreach contract.  Keep the existing GEO execution
# lifecycle above unchanged; this sequence covers recruitment and consent
# gates that occur before a GEO Engine job exists.
OUTREACH_FIRST_LIFECYCLE = (
    "DISCOVERED", "CONTACT_VERIFIED", "PRELIMINARY_GEO_SCREENED",
    "EMAIL_DRAFTED", "INVITED (SIMULATED)", "QUESTIONNAIRE_SUBMITTED (SIMULATED)",
    "CONSENT_VERIFIED", "GEO_HANDOFF", "GEO_PROPERTY_RESOLVED", "WEBSITE_AUDIT",
    "QUESTION_SET_CREATED", "BASELINE_READY", "STRATEGY_RECOMMENDATIONS_READY",
    "REPORT_READY", "IMPLEMENTATION_PENDING", "MONITORING_PENDING",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def question_set(profile: dict[str, Any], *, fixed: bool, website_text: list[str] | None = None) -> dict[str, Any]:
    """Create deterministic, non-provider question pools from supplied evidence."""
    snapshot = profile.get("profile_snapshot", {})
    identity = snapshot.get("identity", {}) if isinstance(snapshot, dict) else {}
    name = profile.get("official_name") or identity.get("name") or "the company"
    industry = snapshot.get("industry") or snapshot.get("sector") or "the company’s category"
    location = snapshot.get("location") or "its service area"
    if fixed:
        texts = [
            f"What does {name} do and who is it for?",
            f"What should a customer in {location} know before choosing {name}?",
            f"What products or services does {name} offer in {industry}?",
        ]
        set_type = "fixed"
    else:
        evidence = " ".join(website_text or [])[:500]
        digest = sha256((name + industry + location + evidence).encode()).hexdigest()[:12]
        texts = [f"What evidence on {name}'s official website explains its main customer outcome? [{digest}]"]
        set_type = "dynamic"
    return {
        "contract_version": "geo-research-integration/v1", "record_type": "evaluation_question_set",
        "schema_version": "geo-research-integration/v1", "record_id": f"questions:{set_type}:{sha256('|'.join(texts).encode()).hexdigest()[:16]}",
        "source_profile_id": profile["source_profile_id"], "source_profile_version": profile["source_profile_version"],
        "property_id": profile.get("property_id"), "question_set_type": set_type,
        "question_set_version": "fixed-v1" if fixed else "dynamic-v1",
        "questions": [{"question_id": f"{set_type}-{index}", "text": text, "intent": "discovery", "source": "deterministic_profile_evidence"}
                      for index, text in enumerate(texts, 1)],
        "created_at": now(), "provenance": {"source_system": "geo-engine", "evidence_only": True},
    }


@dataclass(frozen=True)
class MonitoringPlan:
    profile_id: str
    fixed_question_set_version: str
    cadence: str
    per_company_budget: int
    global_budget: int
    status: str = "paused"

    def authorize_run(self, *, company_used: int, global_used: int, consent_status: str, implementation_verified: bool) -> None:
        if consent_status != "VERIFIED":
            raise ValueError("monitoring blocked: consent is not verified")
        if not implementation_verified:
            raise ValueError("monitoring blocked: deployment verification is required")
        if company_used >= self.per_company_budget or global_used >= self.global_budget:
            raise ValueError("monitoring blocked: budget exhausted")
        if self.status != "active":
            raise ValueError("monitoring plan is not active")
