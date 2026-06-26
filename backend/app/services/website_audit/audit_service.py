from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.website_audit import WebsiteAudit
from app.services.website_audit.analyzer import analyze_brand_understanding
from app.services.website_audit.crawler import crawl_website, normalize_base_url
from app.services.website_audit.extractor import extract_pages
from app.services.website_audit.recommendations import build_recommendations
from app.services.website_audit.repository import (
    create_audit_record,
    get_latest_audit,
)
from app.services.website_audit.scoring import score_website


def run_website_audit(
    db: Session,
    property_record: Property,
) -> WebsiteAudit:
    base_url = normalize_base_url(property_record.domain)
    crawl_responses = crawl_website(property_record.domain)
    pages = extract_pages(crawl_responses)

    brand_understanding = analyze_brand_understanding(
        pages=pages,
        property_name=property_record.name,
        brand_name=property_record.brand_name,
    )
    scores = score_website(pages)
    recommendations = build_recommendations(
        pages=pages,
        scores=scores,
        category_hint=property_record.description or property_record.name,
    )

    return create_audit_record(
        db=db,
        property_id=property_record.id,
        base_url=base_url,
        brand_understanding=brand_understanding,
        scores=scores,
        pages=pages,
        recommendations=recommendations,
    )


def latest_website_audit(
    db: Session,
    property_id: int,
) -> WebsiteAudit | None:
    return get_latest_audit(db=db, property_id=property_id)


def serialize_audit(audit: WebsiteAudit, property_record: Property):
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
