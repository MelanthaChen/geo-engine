"""Deterministic outreach-first integration using GeoAIResume as a fixture."""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

OUTREACH = Path("/Users/melc/Documents/Intern/LLM Search Optimizer/geo-research-outreach-agent")
GEOAIRESUME = Path("/Users/melc/Documents/App Design/GeoAIResume")
sys.path.insert(0, str(OUTREACH / "src"))

from outreach_agent.integration import build_profile_import, discover_public_contact, import_result_envelope  # noqa: E402
from outreach_agent.geo_engine_handoff import review_questionnaire_submission  # noqa: E402
from outreach_agent.research_lifecycle import (  # noqa: E402
    CONSENT_VERSION,
    OUTREACH_FIRST_LIFECYCLE,
    create_geo_handoff,
    approve_email,
    create_email_draft,
    create_questionnaire_invitation,
    init_registry,
    register_profile,
    save_preliminary_screening,
    submit_questionnaire,
    record_simulated_send,
    withdraw_consent,
)

import app.models  # noqa: E402,F401
from app.core.database import Base  # noqa: E402
from app.integration.adapter import GeoResearchIntegrationAdapter  # noqa: E402


class FixtureBridge:
    def import_profile(self, profile):
        return {"property_id": 77, "source_profile_id": profile["profile_id"]}
from app.integration.contracts import validate_record  # noqa: E402
from app.integration.lifecycle import OUTREACH_FIRST_LIFECYCLE as ENGINE_LIFECYCLE  # noqa: E402


def _ts():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def test_geoairesume_outreach_first_lifecycle_is_consent_gated_and_idempotent(tmp_path, monkeypatch):
    assert OUTREACH_FIRST_LIFECYCLE == ENGINE_LIFECYCLE
    fixture_path = GEOAIRESUME / "integration" / "site.json"
    fixture = json.loads(fixture_path.read_text())
    assert fixture["research_fixture"]["classification"] == "owner_controlled_test_site"

    registry = tmp_path / "outreach-registry.db"
    profile = {
        "schema_version": "geo-company-profile/v1",
        "profile_id": "geoairesume-owner-test-v1",
        "profile_type": "owner_controlled_test",
        "identity": {"name": "GeoAIResume", "website": fixture["website"]["canonical_origin"]},
        "startup": {"location": "Boston, Massachusetts, United States"},
        "qualification": {"eligibility": "OWNER_CONTROLLED_TEST"},
    }
    register_profile(profile, registry)
    contact = discover_public_contact(
        source_url=fixture["website"]["canonical_origin"],
        html="<p>Owner-controlled fixture</p><a href='/contact'>Contact</a>",
        captured_at="2026-10-22T12:00:00+00:00",
    )
    assert contact["read_only"] is True
    assert contact["channel_type"] == "NO_CONTACT_CHANNEL"
    draft_id = create_email_draft("geoairesume-owner-test-v1", "owner@example.test", "Simulated research invitation", path=registry)
    approve_email(draft_id, "fixture-reviewer", path=registry)
    assert record_simulated_send(draft_id, path=registry).startswith("email-event-")
    save_preliminary_screening("geoairesume-owner-test-v1", [{"title": "Observed content structure", "claim": "fixture-only"}], [{"url": fixture["website"]["canonical_origin"], "excerpt": "fixture"}], path=registry, provider="mock", model="none", prompt_version="fixture-v1")
    invitation_id, token = create_questionnaire_invitation("geoairesume-owner-test-v1", secret="fixture-secret", path=registry)
    with sqlite3.connect(registry) as db:
        db.execute("UPDATE email_drafts SET invitation_id=? WHERE draft_id=?", (invitation_id, draft_id))
    with pytest.raises(PermissionError, match="explicit website-analysis consent"):
        create_geo_handoff("geoairesume-owner-test-v1", "missing", scope={}, path=registry)

    response = {"respondent_name": "Owner", "respondent_role": "Owner", "contact_email": "owner@example.test", "agree_research": True,
                "company_identity_confirmed": True,
                "website_analysis_allowed": True, "recommendations_requested": True,
                "ongoing_measurement_allowed": True, "site_modification_authorized": False,
                "consent_wording_version": CONSENT_VERSION}
    submission_id = submit_questionnaire(token, secret="fixture-secret", response=response, path=registry)
    assert submit_questionnaire(token, secret="fixture-secret", response=response, path=registry) == submission_id
    with sqlite3.connect(registry) as db:
        db.execute("UPDATE questionnaire_submissions SET research_interest='YES', research_authorization='YES' WHERE submission_id=?", (submission_id,))
    review = review_questionnaire_submission(
        submission_id,
        reviewer="fixture-reviewer",
        company_identity_verified=True,
        representative_authorized=True,
        consent_version_verified=True,
        website_scope_verified=True,
        withdrawal_checked=True,
        approve=True,
        notes="owner-controlled local fixture",
        path=registry,
        bridge=FixtureBridge(),
    )
    assert review["status"] in {"HANDOFF_PENDING", "HANDED_OFF"}
    handoff_id = create_geo_handoff("geoairesume-owner-test-v1", submission_id,
                                    scope={"analysis": "website-only", "fixture_protocol": "OWNER_CONTROLLED_TEST_LOCAL_ONLY"}, path=registry)
    assert handoff_id.startswith("handoff-")

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        adapter = GeoResearchIntegrationAdapter(db, tmp_path / "engine-store")
        source = dict(profile)
        source["consent"] = {"status": "VERIFIED", "consent_id": submission_id, "version": CONSENT_VERSION,
                              "research_scope": ["website_audit", "llm_evaluation"]}
        imported = adapter.import_profile(source)
        retry = adapter.import_profile(source)
        assert imported["property_id"] == retry["property_id"]
        assert len(adapter.store.records("profile_import")) == 1

        fake_page = SimpleNamespace(id=7, url=fixture["website"]["canonical_origin"], content_sha256="fixture-hash", extraction_failure_reason=None)
        recommendation = SimpleNamespace(id=21, priority="high", affected_page_count=1, suggested_strategy="clarify_entity", category="entity_clarity", title="Clarify entity", evidence_url=fake_page.url, observed_evidence="Fixture page evidence")
        fake_audit = SimpleNamespace(id=11, property_id=imported["property_id"], status="completed", base_url=fixture["website"]["canonical_origin"], pages=[fake_page], recommendations=[recommendation])
        monkeypatch.setattr("app.integration.adapter.serialize_audit", lambda *_: {"pages": [{"id": 7, "url": fake_page.url, "content_sha256": fake_page.content_sha256, "extraction_failure_reason": None}]})
        audit = adapter.run_read_only_audit(imported, audit_runner=lambda *_: fake_audit)
        assert audit["audit_id"] == 11
        validate_record("audit_result_reference", audit)
        strategies = adapter.rank_strategies(fake_audit, imported)
        assert strategies["strategies"][0]["strategy_id"] == "clarify_entity"
        questions, _dynamic = adapter.create_question_sets(imported, website_text=["GeoAIResume resume research fixture"])
        assert questions["source_profile_id"] == imported["source_profile_id"]

        now = _ts()
        baseline = {"contract_version": "geo-research-integration/v1", "record_type": "baseline_experiment_reference", "schema_version": "geo-research-integration/v1", "record_id": "baseline:fixture", "source_profile_id": imported["source_profile_id"], "source_profile_version": imported["source_profile_version"], "property_id": imported["property_id"], "experiment_id": "mock-baseline-1", "status": "READY", "results_present": False, "created_at": now, "provenance": {"source_system": "local-mock"}}
        receipt = adapter.record_deployment(record_id="deployment:fixture", proposal_id="proposal:none", approval_status="rejected", source_git_revision=None, content_hash=None, deployed_git_revision=None, vercel_deployment_id=None, public_url=None, verification_status="not_deployed", baseline_experiment_reference=baseline, post_deployment_experiment_reference=None)
        result = {"contract_version": "geo-research-integration/v1", "source_profile_id": imported["source_profile_id"], "source_profile_version": imported["source_profile_version"], "property_id": imported["property_id"], "property_mapping": adapter.store.records("property_identity_mapping")[0], "audit": audit, "strategies": strategies, "question_set": questions, "baseline": baseline, "deployment_receipts": receipt, "report": {"status": "READY", "simulated": True, "company_name": "GeoAIResume"}, "received_at": now, "provenance": {"source_system": "geo-engine-local-mock"}}
        result_path = tmp_path / "results.jsonl"
        assert import_result_envelope(result, result_path)["added"] >= 4
        assert import_result_envelope(result, result_path)["skipped"] >= 4

        plan = adapter.create_monitoring_plan(profile=imported, cadence="monthly", per_company_budget=1, global_budget=1, implementation_verified=False)
        with pytest.raises(ValueError, match="deployment verification"):
            plan.authorize_run(company_used=0, global_used=0, consent_status="VERIFIED", implementation_verified=False)
        assert plan.status == "paused"
    finally:
        db.close()
        engine.dispose()

    withdraw_consent("geoairesume-owner-test-v1", path=registry)
    with pytest.raises(PermissionError):
        create_geo_handoff("geoairesume-owner-test-v1", submission_id, scope={"fixture_protocol": "OWNER_CONTROLLED_TEST_LOCAL_ONLY"}, path=registry)
