import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.integration.adapter import GeoResearchIntegrationAdapter
from app.integration.research_pipeline import run_research_pipeline
from app.integration.contracts import normalize_profile_import, validate_record
from app.models.property import Property
from app.models.query import Query
from app.models.experiment import Experiment


def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def profile(profile_id="p-1", profile_type="business_company", domain="https://example.test"):
    return {"schema_version": "geo-company-profile/v1", "profile_id": profile_id,
            "profile_type": profile_type, "identity": {"name": profile_id, "website_url": domain},
            "cohort_membership": {"smb": profile_type == "business_company", "hotel": profile_type == "hotel_property"},
            "consent": {"status": "VERIFIED", "consent_id": f"consent-{profile_id}", "version": "v1",
                        "research_scope": ["website_audit", "llm_evaluation"]}}


def test_profile_contract_normalizes_legacy_export_and_validates():
    normalized = normalize_profile_import(profile())
    validate_record("profile_import", normalized)
    assert normalized["source_schema_version"] == "geo-company-profile/v1"
    assert normalized["profile_type"] == "business_company"
    assert normalized["source_profile_id"] == "p-1"


def test_missing_or_withdrawn_consent_is_rejected():
    with pytest.raises(ValueError, match="consent"):
        normalize_profile_import({"profile_id": "p", "identity": {"name": "P", "website_url": "https://p.test"}})
    withdrawn = profile(); withdrawn["consent"]["status"] = "WITHDRAWN"
    with pytest.raises(ValueError, match="VERIFIED"):
        normalize_profile_import(withdrawn)


def test_import_is_idempotent_and_reuses_existing_property(tmp_path):
    engine, db = session()
    try:
        db.add(Property(name="Existing", domain="example.test")); db.commit()
        adapter = GeoResearchIntegrationAdapter(db, tmp_path)
        first = adapter.import_profile(profile())
        second = adapter.import_profile(profile())
        assert first == second
        assert db.query(Property).count() == 1
        assert len(adapter.store.records("profile_import")) == 1
    finally:
        db.close(); engine.dispose()


def test_hotel_identity_is_not_merged_by_shared_chain_domain(tmp_path):
    engine, db = session()
    try:
        adapter = GeoResearchIntegrationAdapter(db, tmp_path)
        adapter.import_profile(profile("hotel-1", "hotel_property", "https://chain.example"))
        with pytest.raises(ValueError, match="Distinct hotel properties"):
            adapter.import_profile(profile("hotel-2", "hotel_property", "https://chain.example"))
    finally:
        db.close(); engine.dispose()


def test_owner_controlled_test_is_excluded_and_canonical_demo_is_not_duplicated(tmp_path):
    engine, db = session()
    try:
        db.add(Property(name="GeoAIResume", domain="geo-ai-resume.vercel.app")); db.commit()
        result = GeoResearchIntegrationAdapter(db, tmp_path).import_profile(
            profile("owner-test", "owner_controlled_test", "https://geo-ai-resume.vercel.app"))
        assert result["formal_cohort_memberships"] == []
        assert result["exclusion_reason"] == "CONTROLLED_TEST_FIXTURE"
        assert result["property_id"] == 1
        assert db.query(Property).count() == 1
    finally:
        db.close(); engine.dispose()


def test_owner_controlled_fixture_preserves_noncanonical_demo_domain(tmp_path):
    engine, db = session()
    try:
        result = GeoResearchIntegrationAdapter(db, tmp_path).import_profile(
            profile("whisker-demo", "owner_controlled_test", "https://whisker-haven-demo.vercel.app/"))
        assert result["formal_cohort_memberships"] == []
        assert result["property_domain"] == "whisker-haven-demo.vercel.app"
        assert db.query(Property).count() == 1
        assert db.query(Property).first().domain == "whisker-haven-demo.vercel.app"
    finally:
        db.close(); engine.dispose()


def test_audit_failure_is_saved_with_missing_evidence_state(tmp_path):
    engine, db = session()
    try:
        adapter = GeoResearchIntegrationAdapter(db, tmp_path)
        imported = adapter.import_profile(profile())
        result = adapter.run_read_only_audit(imported, audit_runner=lambda *_: (_ for _ in ()).throw(RuntimeError("no crawl")))
        assert result["status"] == "failed"
        assert result["audit_id"] is None
        assert result["page_refs"] == []
        validate_record("audit_result_reference", result)
    finally:
        db.close(); engine.dispose()


def test_rejected_stale_edit_proposal_and_no_fabricated_results_are_contract_flags():
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    common = {"contract_version":"geo-research-integration/v1", "schema_version":"geo-research-integration/v1",
              "record_id":"edit-1", "source_profile_id":"p", "source_profile_version":"v1", "property_id":1,
              "page_id":2, "proposal_id":"proposal-1", "approval_status":"stale", "evidence_refs":[{"page_id":2}],
              "created_at":now, "provenance":{"source_system":"test"}, "record_type":"exact_text_edit_proposal"}
    validate_record("exact_text_edit_proposal", common)
    baseline = {"contract_version":"geo-research-integration/v1", "record_type":"baseline_experiment_reference",
                "schema_version":"geo-research-integration/v1", "record_id":"baseline-1", "source_profile_id":"p",
                "source_profile_version":"v1", "property_id":1, "experiment_id":"not-run", "status":"not_run",
                "results_present":False, "created_at":now, "provenance":{"source_system":"test"}}
    validate_record("baseline_experiment_reference", baseline)


def test_duplicate_deployment_receipts_are_not_appended_twice(tmp_path):
    engine, db = session()
    try:
        adapter = GeoResearchIntegrationAdapter(db, tmp_path)
        fields = {"record_id":"deployment-1", "proposal_id":"proposal-1", "approval_status":"rejected",
                  "source_git_revision":None, "content_hash":None, "deployed_git_revision":None,
                  "vercel_deployment_id":None, "public_url":None, "verification_status":"not_deployed",
                  "baseline_experiment_reference":None, "post_deployment_experiment_reference":None}
        adapter.record_deployment(**fields); adapter.record_deployment(**fields)
        assert len(adapter.store.records("deployment_receipt")) == 1
    finally:
        db.close(); engine.dispose()


def test_controlled_research_pipeline_persists_all_stages_and_is_idempotent(tmp_path, monkeypatch):
    engine, db = session()
    try:
        adapter_profile = profile("controlled-pipeline", "owner_controlled_test", "https://pipeline.example")

        class FakePage:
            id = 8
            url = "https://pipeline.example/"
            content_sha256 = "fixture-page-hash"
            extraction_failure_reason = None

        class FakeRecommendation:
            id = 22
            priority = "high"
            affected_page_count = 1
            suggested_strategy = "entity_clarity"
            category = "entity_clarity"
            title = "Clarify the entity"
            evidence_url = "https://pipeline.example/"
            observed_evidence = "Observed fixture evidence"

        class FakeAudit:
            id = 12
            property_id = 1
            status = "completed"
            base_url = "https://pipeline.example"
            pages = [FakePage()]
            recommendations = [FakeRecommendation()]

        def audit_runner(_db, property_record):
            FakeAudit.property_id = property_record.id
            return FakeAudit()

        monkeypatch.setattr("app.integration.adapter.serialize_audit", lambda audit, prop: {
            "id": audit.id, "property_id": prop.id, "website_url": audit.base_url,
            "status": audit.status, "pages": [{"id": 8, "url": FakePage.url, "content_sha256": FakePage.content_sha256, "extraction_failure_reason": None}],
        })
        first = run_research_pipeline(db, profile=adapter_profile, store_root=str(tmp_path), audit_runner=audit_runner, allow_controlled_fixture=True)
        second = run_research_pipeline(db, profile=adapter_profile, store_root=str(tmp_path), audit_runner=audit_runner, allow_controlled_fixture=True)
        assert first["status"] == "COMPLETED"
        assert first["idempotent"] is False
        assert second["idempotent"] is True
        assert first["property_id"] == second["result"]["property_id"]
        assert db.query(Property).count() == 1
        assert db.query(Query).count() == 4
        assert db.query(Experiment).count() == 1
        assert len(GeoResearchIntegrationAdapter(db, tmp_path).store.records("research_result_export")) == 1
    finally:
        db.close(); engine.dispose()
