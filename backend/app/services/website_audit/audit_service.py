from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.property import Property
from app.models.website_audit import WebsiteAudit
from app.services.website_audit.analyzer import analyze_brand_understanding
from app.services.website_audit.crawler import crawl_website, normalize_base_url
from app.services.website_audit.extractor import extract_pages
from app.services.website_audit.recommendations import build_recommendations
from app.services.website_audit.repository import (
    create_audit_record,
    get_audit,
    get_latest_audit,
)
from app.services.website_audit.scoring import score_website
from app.services.website_audit.profile import (
    build_findings,
    build_optimization_opportunities,
    build_website_features,
    build_website_profile,
)


def run_website_audit(
    db: Session,
    property_record: Property,
) -> WebsiteAudit:
    base_url = normalize_base_url(property_record.domain)
    crawl_result = crawl_website(
        property_record.domain,
        max_pages=settings.WEBSITE_AUDIT_MAX_PAGES,
    )
    pages = extract_pages(crawl_result.responses)
    evidence_pages = [
        page for page in pages
        if not page.is_duplicate
        and page.status_code is not None
        and 200 <= page.status_code < 300
        and page.body_text
    ]

    brand_understanding = analyze_brand_understanding(
        pages=evidence_pages,
        property_name=property_record.name,
        brand_name=property_record.brand_name,
    )
    scores = score_website(evidence_pages)
    recommendations = (
        build_recommendations(
            pages=evidence_pages,
            scores=scores,
            category_hint=property_record.description or property_record.name,
        )
        if evidence_pages
        else []
    )

    return create_audit_record(
        db=db,
        property_id=property_record.id,
        base_url=base_url,
        brand_understanding=brand_understanding,
        scores=scores,
        pages=pages,
        recommendations=recommendations,
        crawl_coverage=crawl_result.coverage,
    )


def latest_website_audit(
    db: Session,
    property_id: int,
) -> WebsiteAudit | None:
    return get_latest_audit(db=db, property_id=property_id)


def website_audit(
    db: Session,
    property_id: int,
    audit_id: int,
) -> WebsiteAudit | None:
    return get_audit(db=db, property_id=property_id, audit_id=audit_id)


def serialize_audit(audit: WebsiteAudit, property_record: Property):
    strengths, weaknesses = build_findings(audit)
    website_profile = build_website_profile(audit)
    website_profile.pop("_evidence", None)

    return {
        "id": audit.id,
        "property_id": property_record.id,
        "property_name": property_record.name,
        "website_url": audit.base_url,
        "last_audit": (
            audit.completed_at.isoformat()
            if audit.completed_at
            else audit.created_at.isoformat()
        ),
        "status": audit.status,
        "overall_geo_score": audit.overall_geo_score,
        "subscores": {
            "content_coverage": audit.content_coverage_score,
            "faq_coverage": audit.faq_coverage_score,
            "internal_linking": audit.internal_linking_score,
            "website_structure": audit.website_structure_score,
            "brand_clarity": audit.brand_clarity_score,
            "trust_signals": audit.trust_signals_score,
        },
        "brand_understanding": {
            "status": "completed",
            "items": [
                audit.brand_summary,
                f"Product: {audit.product_summary}",
                f"Audience: {audit.target_audience}",
                f"Use cases: {audit.primary_use_cases}",
                f"Value proposition: {audit.core_value_proposition}",
            ],
        },
        "website_profile": website_profile,
        "crawl_coverage": {
            "inventory_source": audit.crawl_inventory_source or "legacy",
            "crawl_limit": audit.crawl_limit,
            "discovered_urls": audit.discovered_url_count or len(audit.pages),
            "requested_urls": audit.requested_url_count or len(audit.pages),
            "successful_responses": audit.successful_response_count
            if audit.successful_response_count is not None
            else sum(page.status_code == 200 for page in audit.pages),
            "accepted_html_responses": audit.accepted_html_response_count,
            "robots_txt_detected": (
                bool(audit.robots_txt_detected)
                if audit.robots_txt_detected is not None
                else None
            ),
            "sitemap_detected": (
                audit.crawl_inventory_source == "sitemap"
                if audit.crawl_inventory_source is not None
                else None
            ),
            "sitemap_url_count": audit.sitemap_url_count,
            "successful_extractions": audit.extraction_success_count,
            "unique_content_pages": audit.unique_content_count
            if audit.unique_content_count is not None
            else sum(not getattr(page, "is_duplicate", False) for page in audit.pages),
            "duplicate_fallback_responses": audit.duplicate_content_count or 0,
            "skipped_due_to_limit": audit.skipped_due_to_limit_count or 0,
            "truncated": bool(audit.skipped_due_to_limit_count),
            "analysis_status": audit.status,
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        "website_features": build_website_features(audit),
        "optimization_opportunities": build_optimization_opportunities(audit),
        "pages": [
            {
                "id": page.id,
                "url": page.url,
                "page_title": page.page_title,
                "meta_description": page.meta_description,
                "h1": page.h1,
                "status_code": page.status_code,
                "word_count": page.word_count,
                "internal_link_count": page.internal_link_count,
                "external_link_count": page.external_link_count,
                "content_sha256": page.content_sha256,
                "is_duplicate": page.is_duplicate,
                "duplicate_of_url": page.duplicate_of_url,
            }
            for page in audit.pages
        ],
        "missing_pages": recommendation_items(audit, "missing_pages"),
        "missing_geo_topics": recommendation_items(audit, "missing_geo_topics"),
        "internal_linking_suggestions": recommendation_items(
            audit,
            "internal_linking_suggestions",
        ),
        "faq_opportunities": recommendation_items(audit, "faq_opportunities"),
        "content_recommendations": recommendation_items(
            audit,
            "content_recommendations",
        ),
    }


def recommendation_items(audit: WebsiteAudit, category: str) -> list[str]:
    return [
        format_recommendation(recommendation)
        for recommendation in audit.recommendations
        if recommendation.category == category
    ]


def format_recommendation(recommendation) -> str:
    evidence = (
        f" Evidence: {recommendation.evidence_url}"
        if recommendation.evidence_url
        else ""
    )

    return (
        f"[{recommendation.priority.upper()}] "
        f"{recommendation.title}: {recommendation.description}"
        f"{evidence}"
    )
