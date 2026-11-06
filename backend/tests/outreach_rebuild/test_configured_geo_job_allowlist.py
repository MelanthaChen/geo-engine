from app.integration.durable_outreach import AUTHORIZED_TEST_WEBSITE, authorized_single_job
key = "outreach-v2:inv-fresh-owner-test"
ref = "GEO-FRESH-REFERENCE"
email = "owner@example.com"
binding = {"candidate_id":"fresh-owner", "invitation_id":"inv-clean", "invitation_reference":ref, "website":AUTHORIZED_TEST_WEBSITE, "invitation_recipient":"owner@outlook.com", "verified_respondent_email":email, "identity_source":"GOOGLE_FORMS_VERIFIED_RESPONDENT_EMAIL", "authorization":"EXPLICIT_OWNER_CONTROLLED_STAGING_BINDING", "recorded_at":"2026-11-05T00:00:00Z"}
profile = {"profile_id":"fresh-owner", "profile_version":"inv-clean", "profile_type":"owner_controlled_test", "controlled_fixture":False, "identity":{"website":AUTHORIZED_TEST_WEBSITE}, "consent":{"status":"VERIFIED", "research_interest":"YES", "research_authorization":"YES", "scope_website":AUTHORIZED_TEST_WEBSITE, "submission_id":"outreach-submission-row-9", "invitation_reference":ref, "verified_identity":{"provider":"GOOGLE_FORMS_VERIFIED", "email":email, "response_id":"google-response-23"}, "owner_identity_binding":binding}}
def test_exact_job_requires_verified_owner_binding(): assert authorized_single_job(key, profile, True, key); assert not authorized_single_job(key, profile, True, "outreach-v2:other"); assert not authorized_single_job(key, profile, False, key); assert not authorized_single_job(key, profile, True, ""); assert not authorized_single_job(key, {**profile, "identity":{"website":"https://other.example/"}}, True, key); assert not authorized_single_job(key, {**profile, "consent":{**profile["consent"], "research_authorization":"NO"}}, True, key); assert not authorized_single_job(key, {**profile, "consent":{**profile["consent"], "verified_identity":{**profile["consent"]["verified_identity"], "provider":"SELF_REPORTED"}}}, True, key); assert not authorized_single_job(key, {**profile, "consent":{**profile["consent"], "owner_identity_binding":{**binding, "identity_source":"SELF_REPORTED"}}}, True, key); assert not authorized_single_job(key, {**profile, "consent":{**profile["consent"], "invitation_reference":"other"}}, True, key)


def test_google_response_id_is_distinct_from_outreach_submission_id():
    assert profile['consent']['submission_id'] != profile['consent']['verified_identity']['response_id']
    assert authorized_single_job(key, profile, True, key)


def test_missing_google_response_id_still_fails_closed():
    consent = {**profile['consent'], 'verified_identity': {**profile['consent']['verified_identity'], 'response_id': ''}}
    assert not authorized_single_job(key, {**profile, 'consent': consent}, True, key)
