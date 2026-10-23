from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.integration.contracts import (
    CANONICAL_GEOAIRESUME_URL,
    _domain,
    normalize_profile_import,
    sha256_json,
    utc_now,
    validate_record,
)
from app.integration.store import AppendOnlyJsonlStore
from app.integration.lifecycle import question_set, now, MonitoringPlan, LIFECYCLE
from app.models.property import Property
from app.models.query import Query
from app.models.experiment import Experiment
from app.services.property_service import create_property
from app.services.website_audit.audit_service import run_website_audit, serialize_audit


class GeoResearchIntegrationAdapter:
    def __init__(self, db: Session, store_root: str | Path):
        self.db = db
        self.store = AppendOnlyJsonlStore(store_root)

    def import_profile(self, source_profile: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_profile_import(source_profile)
        validate_record("profile_import", normalized)
        prior = self.store.find_profile(normalized["source_profile_id"], normalized["source_profile_version"])
        if prior:
            return prior

        domain = _domain(normalized["official_domain"])
        property_record = self.db.query(Property).filter(Property.domain == domain).first()
        mapping_action = "reused" if property_record else "created"
        # The canonical demo is matched by canonical URL/domain, never duplicated.
        if not property_record and domain == _domain(CANONICAL_GEOAIRESUME_URL):
            property_record = self.db.query(Property).filter(Property.domain == domain).first()
        if property_record and normalized["profile_type"] == "hotel_property":
            existing = self.store.records("profile_import")
            same_identity = any(item.get("property_id") == property_record.id and
                                item.get("source_profile_id") == normalized["source_profile_id"]
                                for item in existing)
            if not same_identity and any(item.get("property_id") == property_record.id and
                                         item.get("source_profile_id") != normalized["source_profile_id"]
                                         for item in existing):
                raise ValueError("Distinct hotel properties cannot share a GEO Engine Property; explicit property mapping is required")
        if not property_record:
            property_record = create_property(self.db, normalized["official_name"], domain, normalized["official_name"])
        normalized["property_id"] = property_record.id
        normalized["property_domain"] = property_record.domain
        normalized["exclusion_reason"] = (
            "CONTROLLED_TEST_FIXTURE" if normalized["profile_type"] == "owner_controlled_test" else None
        )
        normalized["updated_at"] = utc_now()
        validate_record("profile_import", normalized)
        self.store.append("profile_import", normalized)
        mapping = {
            "contract_version": "geo-research-integration/v1", "record_type": "property_identity_mapping",
            "schema_version": "geo-research-integration/v1", "record_id": f"property-map:{normalized['source_profile_id']}:{property_record.id}",
            "source_profile_id": normalized["source_profile_id"], "source_profile_version": normalized["source_profile_version"],
            "property_id": property_record.id, "mapping_action": mapping_action,
            "mapped_at": utc_now(), "provenance": {"source_system": "geo-engine", "profile_import_record_id": normalized["record_id"]},
        }
        validate_record("property_identity_mapping", mapping)
        self.store.append("property_identity_mapping", mapping)
        return normalized

    def run_read_only_audit(self, profile: dict[str, Any], audit_runner: Callable | None = None) -> dict[str, Any]:
        property_id = profile.get("property_id")
        property_record = self.db.query(Property).filter(Property.id == property_id).first()
        if not property_record:
            raise ValueError(f"Unknown GEO Engine property: {property_id}")
        try:
            audit = (audit_runner or run_website_audit)(self.db, property_record)
            serialized = serialize_audit(audit, property_record)
            envelope = {
                "contract_version": "geo-research-integration/v1",
                "record_type": "audit_result_reference",
                "schema_version": "geo-research-integration/v1",
                "record_id": f"audit-result:{audit.id}",
                "source_profile_id": profile["source_profile_id"],
                "source_profile_version": profile["source_profile_version"],
                "property_id": property_record.id,
                "audit_id": audit.id,
                "status": audit.status,
                "audit_url": audit.base_url,
                "page_refs": [{"page_id": page["id"], "url": page["url"], "evidence_hash": page["content_sha256"],
                               "failure_state": page["extraction_failure_reason"]} for page in serialized.get("pages", [])],
                "captured_at": utc_now(),
                "provenance": {"source_system": "geo-engine", "audit_id": audit.id, "property_id": property_record.id},
            }
        except Exception as exc:
            envelope = {
                "contract_version": "geo-research-integration/v1", "record_type": "audit_result_reference",
                "schema_version": "geo-research-integration/v1", "record_id": f"audit-result-failed:{profile['source_profile_id']}:{utc_now()}",
                "source_profile_id": profile["source_profile_id"], "source_profile_version": profile["source_profile_version"],
                "property_id": property_record.id, "audit_id": None, "status": "failed", "audit_url": property_record.domain,
                "page_refs": [], "captured_at": utc_now(), "failure_state": str(exc),
                "provenance": {"source_system": "geo-engine", "property_id": property_record.id},
            }
        validate_record("audit_result_reference", envelope)
        self.store.append("audit_result_reference", envelope)
        return envelope

    def rank_strategies(self, audit: Any, profile: dict[str, Any]) -> dict[str, Any]:
        """Expose existing evidence recommendations as a rule-based top-three."""
        priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations = sorted(
            getattr(audit, "recommendations", []) or [],
            key=lambda item: (priority.get(item.priority, 9), -(item.affected_page_count or 0), item.id),
        )[:3]
        record = {
            "contract_version": "geo-research-integration/v1", "record_type": "ranked_strategy_recommendation",
            "schema_version": "geo-research-integration/v1", "record_id": f"strategies:{audit.id}",
            "source_profile_id": profile["source_profile_id"], "source_profile_version": profile["source_profile_version"],
            "property_id": audit.property_id, "audit_id": audit.id,
            "ranking_policy": "rule_based_existing_recommendations",
            "strategies": [{"rank": index, "strategy_id": getattr(item, "suggested_strategy", None) or item.category,
                            "recommendation_id": item.id, "title": item.title,
                            "evidence_refs": [{"url": item.evidence_url, "observed_evidence": item.observed_evidence}]}
                           for index, item in enumerate(recommendations, 1)],
            "created_at": utc_now(), "provenance": {"source_system": "geo-engine", "audit_id": audit.id},
        }
        validate_record("ranked_strategy_recommendation", record)
        self.store.append("ranked_strategy_recommendation", record)
        return record

    def create_question_sets(self, profile: dict[str, Any], website_text: list[str] | None = None) -> tuple[dict, dict]:
        fixed = question_set(profile, fixed=True)
        dynamic = question_set(profile, fixed=False, website_text=website_text)
        validate_record("evaluation_question_set", fixed)
        validate_record("evaluation_question_set", dynamic)
        self.store.append("evaluation_question_set", fixed)
        self.store.append("evaluation_question_set", dynamic)
        return fixed, dynamic

    def record_implementation(self, *, profile: dict[str, Any], proposal_ids: list[str], page_refs: list[dict],
                              owner_evidence_ref: str | None, verified_content_hash: str | None,
                              verification_status: str) -> dict:
        record = {
            "contract_version": "geo-research-integration/v1", "record_type": "implementation_record",
            "schema_version": "geo-research-integration/v1", "record_id": f"implementation:{profile['source_profile_id']}:{now()}",
            "source_profile_id": profile["source_profile_id"], "source_profile_version": profile["source_profile_version"],
            "property_id": profile.get("property_id"), "proposal_ids": proposal_ids, "page_refs": page_refs,
            "owner_evidence_ref": owner_evidence_ref, "verified_content_hash": verified_content_hash,
            "verification_status": verification_status, "implemented_at": now(),
            "provenance": {"source_system": "owner-provided", "verified_by": "owner_evidence" if owner_evidence_ref else None},
        }
        self.store.append("implementation_record", record)
        return record

    def create_monitoring_plan(self, *, profile: dict[str, Any], cadence: str, per_company_budget: int,
                               global_budget: int, implementation_verified: bool) -> MonitoringPlan:
        if not profile.get("consent", {}).get("status") == "VERIFIED":
            raise ValueError("monitoring requires verified consent")
        plan = MonitoringPlan(profile["source_profile_id"], "fixed-v1", cadence,
                              per_company_budget, global_budget,
                              "active" if implementation_verified else "paused")
        self.store.append("monitoring_plan", {"contract_version": "geo-research-integration/v1",
                         "record_type": "monitoring_plan", "schema_version": "geo-research-integration/v1",
                         "record_id": f"monitoring:{profile['source_profile_id']}", "profile_id": plan.profile_id,
                         "fixed_question_set_version": plan.fixed_question_set_version, "cadence": cadence,
                         "per_company_budget": per_company_budget, "global_budget": global_budget,
                         "status": plan.status, "created_at": now(),
                         "provenance": {"source_system": "geo-engine"}})
        return plan

    def record_deployment(self, **fields: Any) -> dict[str, Any]:
        record = {"contract_version": "geo-research-integration/v1", "record_type": "deployment_receipt",
                  "schema_version": "geo-research-integration/v1", "record_id": fields.get("record_id") or f"deployment:{sha256_json(fields)}",
                  "recorded_at": utc_now(), "provenance": {"source_system": "geo-engine"}, **fields}
        validate_record("deployment_receipt", record)
        # Duplicate receipts are retained as a replay-safe no-op at the adapter boundary.
        if not any(item.get("record_id") == record["record_id"] for item in self.store.records("deployment_receipt")):
            self.store.append("deployment_receipt", record)
        return record

    def create_query_universe(self, *, profile: dict[str, Any], questions: list[str]) -> dict[str, Any]:
        """Persist a deterministic query universe without invoking a provider."""
        property_id = profile.get("property_id")
        query_ids = []
        for text in questions:
            existing = self.db.query(Query).filter(Query.query_text == text).first()
            if existing is None:
                existing = Query(
                    property_id=property_id,
                    category=profile.get("official_name", "company"),
                    niche=profile.get("official_name", "company"),
                    query_text=text,
                    query_type="controlled_fixture",
                )
                self.db.add(existing)
                self.db.flush()
            query_ids.append(existing.id)
        self.db.commit()
        record = {
            "contract_version": "geo-research-integration/v1",
            "record_type": "query_universe_reference",
            "schema_version": "geo-research-integration/v1",
            "record_id": f"query-universe:{profile['source_profile_id']}:{profile['source_profile_version']}",
            "source_profile_id": profile["source_profile_id"],
            "source_profile_version": profile["source_profile_version"],
            "property_id": property_id,
            "query_ids": query_ids,
            "queries": questions,
            "status": "READY",
            "created_at": utc_now(),
            "provenance": {"source_system": "geo-engine", "provider": "CONTROLLED_FIXTURE"},
        }
        if not any(item.get("record_id") == record["record_id"] for item in self.store.records("query_universe_reference")):
            self.store.append("query_universe_reference", record)
        return record

    def record_baseline(self, *, profile: dict[str, Any], experiment_id: int | str, results: dict[str, Any]) -> dict[str, Any]:
        """Persist a baseline reference; provider results are supplied by the caller."""
        record = {
            "contract_version": "geo-research-integration/v1",
            "record_type": "baseline_experiment_reference",
            "schema_version": "geo-research-integration/v1",
            "record_id": f"baseline:{profile['source_profile_id']}:{experiment_id}",
            "source_profile_id": profile["source_profile_id"],
            "source_profile_version": profile["source_profile_version"],
            "property_id": profile.get("property_id"),
            "experiment_id": experiment_id,
            "status": "COMPLETED",
            "results_present": bool(results),
            "results": results,
            "created_at": utc_now(),
            "provenance": {"source_system": "geo-engine", "provider": results.get("provider", "CONTROLLED_FIXTURE")},
        }
        if not any(item.get("record_id") == record["record_id"] for item in self.store.records("baseline_experiment_reference")):
            self.store.append("baseline_experiment_reference", record)
        return record

    def export_research_result(self, *, profile: dict[str, Any], audit_reference: dict[str, Any], strategies: dict[str, Any], question_set_reference: dict[str, Any] | None, baseline_reference: dict[str, Any] | None, post_deployment_reference: dict[str, Any] | None = None) -> dict[str, Any]:
        """Persist the complete result envelope for authenticated Outreach retrieval."""
        record = {
            "contract_version": "geo-research-integration/v1",
            "record_type": "research_result_export",
            "schema_version": "geo-research-integration/v1",
            "record_id": f"research-result:{profile['source_profile_id']}:{profile['source_profile_version']}",
            "source_profile_id": profile["source_profile_id"],
            "source_profile_version": profile["source_profile_version"],
            "property_id": profile.get("property_id"),
            "audit_reference": audit_reference,
            "strategies": strategies.get("strategies", [])[:3],
            "question_set_reference": question_set_reference,
            "baseline_reference": baseline_reference,
            "post_deployment_reference": post_deployment_reference,
            "exported_at": utc_now(),
            "provenance": {"source_system": "geo-engine", "research_scope": "public_website_analysis"},
        }
        validate_record("research_result_export", record)
        existing = next((item for item in self.store.records("research_result_export") if item.get("record_id") == record["record_id"]), None)
        if existing:
            return existing
        self.store.append("research_result_export", record)
        return record
