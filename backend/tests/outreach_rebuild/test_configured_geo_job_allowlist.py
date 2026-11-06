import pytest

from app.integration.durable_outreach import authorized_single_job


@pytest.mark.parametrize(("candidate_id", "invitation_id", "website", "email"), [
    ("sim-company-one", "inv-sim-one", "https://one.example/", "contact@one.example"),
    ("sim-company-two", "inv-sim-two", "https://two.example/", "contact@two.example"),
])
def test_exact_job_allowlist_uses_generic_independently_verified_consent(candidate_id, invitation_id, website, email):
    key = "outreach-v2:" + invitation_id
    reference = "REF-" + candidate_id
    profile = {
        "profile_id": candidate_id,
        "profile_version": invitation_id,
        "invitation_id": invitation_id,
        "invitation_recipient": email,
        "identity": {"website": website},
        "consent": {
            "status": "VERIFIED", "research_interest": "YES", "research_authorization": "YES",
            "scope_website": website, "submission_id": "submission-" + candidate_id,
            "invitation_reference": reference, "representative_email": email,
            "verified_identity": {"provider": "GOOGLE_FORMS_VERIFIED", "email": email,
                                  "response_id": "google-response-" + candidate_id},
        },
    }
    assert authorized_single_job(key, profile, True, key)
    assert not authorized_single_job(key, profile, True, "outreach-v2:inv-other")
    assert not authorized_single_job(key, profile, False, key)
    assert not authorized_single_job(key, {**profile, "identity": {"website": "https://other.example/"}}, True, key)
    bad_consent = {**profile, "consent": {**profile["consent"], "research_authorization": "NO"}}
    assert not authorized_single_job(key, bad_consent, True, key)
    no_google_identity = {**profile, "consent": {**profile["consent"],
        "verified_identity": {**profile["consent"]["verified_identity"], "provider": "SELF_REPORTED"}}}
    assert not authorized_single_job(key, no_google_identity, True, key)


def test_cross_account_identity_binding_is_job_website_and_reference_bound():
    key = "outreach-v2:inv-bound"
    website = "https://simulated-company.example/"
    reference = "GEO-BOUND-1"
    binding = {
        "candidate_id": "candidate-bound", "invitation_id": "inv-bound",
        "invitation_reference": reference, "website": website,
        "invitation_recipient": "contact@simulated-company.example",
        "verified_respondent_email": "researcher@gmail.com",
        "identity_source": "GOOGLE_FORMS_VERIFIED_RESPONDENT_EMAIL",
        "authorization": "EXPLICIT_OWNER_CONTROLLED_STAGING_BINDING",
        "recorded_at": "2026-11-05T00:00:00Z",
    }
    profile = {
        "profile_id": "candidate-bound", "profile_version": "inv-bound", "invitation_id": "inv-bound",
        "invitation_recipient": "contact@simulated-company.example", "identity": {"website": website},
        "consent": {"status": "VERIFIED", "research_interest": "YES", "research_authorization": "YES",
            "scope_website": website, "submission_id": "submission-bound", "invitation_reference": reference,
            "verified_identity": {"provider": "GOOGLE_FORMS_VERIFIED", "email": "researcher@gmail.com",
                "response_id": "google-response-bound"}, "owner_identity_binding": binding},
    }
    assert authorized_single_job(key, profile, True, key)
    bad_reference = {**profile, "consent": {**profile["consent"], "invitation_reference": "GEO-OTHER"}}
    assert not authorized_single_job(key, bad_reference, True, key)
