from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.database import Base
from app.models.property import Property
from app.services.website_audit.analyzer import BrandUnderstanding
from app.services.website_audit.crawler import CrawlCoverage
from app.services.website_audit.crawler import CrawlResponse, CrawlResult
from app.services.website_audit.extractor import PageExtract
from app.services.website_audit.repository import create_audit_record
from app.services.website_audit.scoring import score_website
from app.services.website_audit import audit_service


def brand_understanding():
    return BrandUnderstanding(
        brand_summary="No analyzable evidence.",
        product_summary="Unavailable",
        target_audience="Unavailable",
        primary_use_cases="Unavailable",
        core_value_proposition="Unavailable",
    )


def coverage(*, accepted_html=0, successful=1):
    return CrawlCoverage(
        inventory_source="sitemap",
        crawl_limit=20,
        sample_page_limit=10,
        discovered_urls=1,
        selected_urls=1,
        not_selected_due_to_sampling=0,
        requested_urls=1,
        successful_responses=successful,
        accepted_html_responses=accepted_html,
        skipped_due_to_limit=0,
    )


def test_zero_evidence_scores_are_unavailable_and_audit_is_not_completed():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        property_record = Property(name="External site", domain="https://example.com")
        session.add(property_record)
        session.commit()
        scores = score_website([])

        audit = create_audit_record(
            db=session,
            property_id=property_record.id,
            base_url="https://example.com/",
            brand_understanding=brand_understanding(),
            scores=scores,
            pages=[],
            recommendations=[],
            crawl_coverage=coverage(),
        )

        assert audit.status == "insufficient_analyzable_content"
        assert audit.overall_geo_score is None
        assert audit.content_coverage_score is None
        assert audit.website_structure_score is None
        assert audit.trust_signals_score is None
        assert audit.recommendations == []
        assert audit.unique_content_count == 0
        assert audit.extraction_success_count == 0
    finally:
        session.close()
        engine.dispose()


def test_zero_extraction_pipeline_generates_no_optimization_opportunities(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        property_record = Property(name="External site", domain="https://example.com")
        session.add(property_record)
        session.commit()
        monkeypatch.setattr(
            audit_service,
            "crawl_website",
            lambda *_args, **_kwargs: CrawlResult(
                responses=[CrawlResponse(
                    url="https://example.com/sitemap-child.xml",
                    status_code=200,
                    html="",
                    content_type="application/xml",
                    html_accepted=False,
                )],
                coverage=coverage(),
            ),
        )

        audit = audit_service.run_website_audit(session, property_record)

        assert audit.status == "insufficient_analyzable_content"
        assert audit.overall_geo_score is None
        assert audit.recommendations == []
        assert audit.successful_response_count == 1
        assert audit.accepted_html_response_count == 0
        assert audit.extraction_success_count == 0
        assert audit.unique_content_count == 0
    finally:
        session.close()
        engine.dispose()


def test_normal_html_evidence_preserves_completed_scoring_behavior():
    page = PageExtract(
        url="https://example.com/",
        page_title="Example",
        meta_description="A useful example site",
        h1="Example",
        status_code=200,
        word_count=500,
        internal_link_count=3,
        external_link_count=1,
        body_text="Useful guide content",
        content_sha256="a" * 64,
    )

    scores = score_website([page])

    assert scores.overall_geo_score is not None
    assert scores.content_coverage_score == 28


def test_duplicate_html_is_not_counted_as_unique_scientific_evidence():
    original = PageExtract(
        url="https://example.com/",
        page_title="Example",
        meta_description=None,
        h1="Example",
        status_code=200,
        word_count=10,
        internal_link_count=1,
        external_link_count=0,
        body_text="Same content",
        content_sha256="b" * 64,
    )
    duplicate = PageExtract(
        url="https://example.com/fallback",
        page_title="Example",
        meta_description=None,
        h1="Example",
        status_code=200,
        word_count=10,
        internal_link_count=1,
        external_link_count=0,
        body_text="Same content",
        content_sha256="b" * 64,
        is_duplicate=True,
        duplicate_of_url="https://example.com/",
    )

    unique = [page for page in [original, duplicate] if not page.is_duplicate]
    assert len(unique) == 1
    assert score_website(unique).content_coverage_score == 24
