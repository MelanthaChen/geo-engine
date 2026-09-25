from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.website_audit import WebsiteAudit
from app.models.website_audit_recommendation import WebsiteAuditRecommendation
from app.models.website_page import WebsitePage
from app.repositories.history_repository import create_history_event
from app.services.website_audit.analyzer import BrandUnderstanding
from app.services.website_audit.crawler import CrawlCoverage
from app.services.website_audit.extractor import PageExtract
from app.services.website_audit.recommendations import AuditRecommendation
from app.services.website_audit.scoring import AuditScores


def create_audit_record(
    db: Session,
    property_id: int,
    base_url: str,
    brand_understanding: BrandUnderstanding,
    scores: AuditScores,
    pages: list[PageExtract],
    recommendations: list[AuditRecommendation],
    crawl_coverage: CrawlCoverage,
) -> WebsiteAudit:
    now = datetime.now(timezone.utc)
    unique_pages = [
        page for page in pages
        if not page.is_duplicate
        and page.status_code is not None
        and 200 <= page.status_code < 300
        and page.body_text
    ]
    duplicate_count = sum(page.is_duplicate for page in pages)
    audit = WebsiteAudit(
        property_id=property_id,
        base_url=base_url,
        status="completed",
        brand_summary=brand_understanding.brand_summary,
        product_summary=brand_understanding.product_summary,
        target_audience=brand_understanding.target_audience,
        primary_use_cases=brand_understanding.primary_use_cases,
        core_value_proposition=brand_understanding.core_value_proposition,
        overall_geo_score=scores.overall_geo_score,
        content_coverage_score=scores.content_coverage_score,
        faq_coverage_score=scores.faq_coverage_score,
        internal_linking_score=scores.internal_linking_score,
        website_structure_score=scores.website_structure_score,
        brand_clarity_score=scores.brand_clarity_score,
        trust_signals_score=scores.trust_signals_score,
        crawl_inventory_source=crawl_coverage.inventory_source,
        crawl_limit=crawl_coverage.crawl_limit,
        discovered_url_count=crawl_coverage.discovered_urls,
        requested_url_count=crawl_coverage.requested_urls,
        successful_response_count=crawl_coverage.successful_responses,
        unique_content_count=len(unique_pages),
        duplicate_content_count=duplicate_count,
        skipped_due_to_limit_count=crawl_coverage.skipped_due_to_limit,
        completed_at=now,
    )

    db.add(audit)
    db.flush()

    for page in pages:
        db.add(
            WebsitePage(
                audit_id=audit.id,
                url=page.url,
                page_title=page.page_title,
                meta_description=page.meta_description,
                h1=page.h1,
                status_code=page.status_code,
                word_count=page.word_count,
                internal_link_count=page.internal_link_count,
                external_link_count=page.external_link_count,
                content_sha256=page.content_sha256,
                is_duplicate=page.is_duplicate,
                duplicate_of_url=page.duplicate_of_url,
            )
        )

    for recommendation in recommendations:
        db.add(
            WebsiteAuditRecommendation(
                audit_id=audit.id,
                category=recommendation.category,
                title=recommendation.title,
                description=recommendation.description,
                priority=recommendation.priority,
                evidence_url=recommendation.evidence_url,
            )
        )

    db.commit()
    db.refresh(audit)

    create_history_event(
        db=db,
        event_type="audit_run",
        property_id=property_id,
        website_audit_id=audit.id,
        status="finished",
        summary=(
            f"Website audit completed with health score "
            f"{scores.overall_geo_score}"
        ),
        details=(
            f"Requested {len(pages)} URLs, analyzed {len(unique_pages)} unique pages, and identified "
            f"{len(recommendations)} candidate opportunities."
        ),
    )

    return audit


def get_latest_audit(
    db: Session,
    property_id: int,
) -> WebsiteAudit | None:
    return (
        db.query(WebsiteAudit)
        .filter(WebsiteAudit.property_id == property_id)
        .order_by(WebsiteAudit.created_at.desc())
        .first()
    )


def get_audit(
    db: Session,
    property_id: int,
    audit_id: int,
) -> WebsiteAudit | None:
    return (
        db.query(WebsiteAudit)
        .filter(
            WebsiteAudit.id == audit_id,
            WebsiteAudit.property_id == property_id,
        )
        .first()
    )
