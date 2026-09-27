from app.services.website_audit.extractor import PageExtract
from app.services.website_audit.profile import build_findings, build_optimization_opportunities
from app.services.website_audit.recommendations import build_recommendations
from app.models.website_audit import WebsiteAudit
from app.models.website_audit_recommendation import WebsiteAuditRecommendation
from app.models.website_page import WebsitePage


def page(**overrides):
    values = {
        "url": "https://example.com/article",
        "page_title": "Article",
        "meta_description": "A factual article",
        "h1": "Article heading",
        "status_code": 200,
        "word_count": 300,
        "internal_link_count": 4,
        "external_link_count": 1,
        "body_text": "Article body without generic commerce page types.",
        "content_sha256": "a" * 64,
    }
    values.update(overrides)
    return PageExtract(**values)


def test_generic_page_type_absence_does_not_generate_opportunities():
    recommendations = build_recommendations(
        [page()],
        requested_urls=1,
        accepted_html_responses=1,
    )

    assert recommendations == []


def test_opportunities_include_counts_observation_and_rationale():
    recommendations = build_recommendations(
        [page(h1=None, meta_description=None, internal_link_count=1)],
        requested_urls=3,
        accepted_html_responses=1,
    )

    by_category = {item.category: item for item in recommendations}
    assert "missing_pages" not in by_category
    assert "faq_opportunities" not in by_category
    assert by_category["heading_structure"].observed_evidence == (
        "1 of 1 analyzed pages have no detected H1."
    )
    assert by_category["heading_structure"].affected_page_count == 1
    assert by_category["heading_structure"].evaluated_page_count == 1
    assert by_category["heading_structure"].why_it_matters
    assert by_category["http_html_success"].observed_evidence == (
        "2 of 3 requested URLs did not return a successful accepted HTML response."
    )
    assert by_category["internal_linking_suggestions"].affected_page_count == 1


def test_findings_use_requested_url_denominator():
    audit = WebsiteAudit(
        requested_url_count=200,
        successful_response_count=192,
        accepted_html_response_count=192,
        extraction_success_count=1,
        pages=[WebsitePage(
            url="https://example.com/",
            status_code=200,
            word_count=100,
            internal_link_count=1,
            external_link_count=0,
            content_sha256="a" * 64,
            is_duplicate=False,
        )],
    )

    strengths, weaknesses = build_findings(audit)

    assert strengths[0]["evidence"] == (
        "192 of 200 requested URLs returned successful HTTP responses."
    )
    assert any("8 of 200 requested URLs" in item["evidence"] for item in weaknesses)


def test_historical_generic_absence_is_not_exposed_as_an_opportunity():
    audit = WebsiteAudit(recommendations=[WebsiteAuditRecommendation(
        category="missing_pages",
        title="Create a pricing page",
        description="Pricing was absent.",
        priority="medium",
    )])

    assert build_optimization_opportunities(audit) == []


def test_faq_recommendation_depends_on_explanatory_content_not_url_absence():
    recommendations = build_recommendations(
        [page(
            url="https://example.com/guide",
            body_text="This guide explains how the service works and helps readers understand each step.",
            word_count=350,
        )],
        requested_urls=1,
        accepted_html_responses=1,
    )

    faq = next(item for item in recommendations if item.category == "faq_opportunities")
    assert faq.affected_page_count == 1
    assert "no detected FAQPage schema" in faq.observed_evidence
    assert "/faq" not in faq.observed_evidence


def test_url_named_faq_does_not_create_a_recommendation_without_content_evidence():
    recommendations = build_recommendations(
        [page(
            url="https://example.com/faq",
            body_text="Short contact details.",
            word_count=40,
        )],
        requested_urls=1,
        accepted_html_responses=1,
    )

    assert not any(item.category == "faq_opportunities" for item in recommendations)


def test_strong_existing_faq_structure_is_not_prioritized():
    recommendations = build_recommendations(
        [page(
            url="https://example.com/support",
            body_text="How does the service work? It explains each step in detail.",
            word_count=350,
            question_heading_count=3,
            detected_qa_pair_count=3,
            faq_like_heading_count=1,
            faq_page_schema_detected=True,
        )],
        requested_urls=1,
        accepted_html_responses=1,
    )

    assert not any(item.category == "faq_opportunities" for item in recommendations)
