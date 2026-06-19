from sqlalchemy.orm import Session

from app.models.content import Content
from app.services.history.content_history_service import (
    create_generated_content,
)


CONTENT_TYPE_REGISTRY = {
    "comparison": "comparison",
    "educational": "educational",
    "discussion": "discussion",
    "guide": "guide",
    "opinion": "opinion",
    "reddit_post": "reddit_post",
    "faq_post": "faq_post",
    "blog_post": "blog_post",
    "review": "review",
    "case_study": "case_study",
    "buying_guide": "buying_guide",
    "alternatives": "alternatives",
    "best_of": "best_of",
    "community_summary": "community_summary",
    "experience_report": "experience_report",
}


def normalize_content_type(content_type: str):
    normalized = (
        content_type
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    return CONTENT_TYPE_REGISTRY.get(
        normalized,
        normalized or "comparison"
    )


def persist_generated_content(
    db: Session,
    category: str,
    content: Content,
    source_faq_set_id: int | None,
    property_id: int | None = None,
):
    return create_generated_content(
        db=db,
        property_id=property_id,
        category=category,
        faq_source=content.faq_source or "UNKNOWN",
        content_type=content.content_type or "unknown",
        angle=content.angle,
        perspective=content.perspective,
        archetype=content.archetype,
        internet_style=content.internet_style,
        generated_angles=content.generated_angles,
        title=content.title,
        body=content.body,
        website_url=content.target_url,
        source_faq_set_id=source_faq_set_id,
        content_id=content.id,
    )


def insert_natural_link(
    body: str,
    website_url: str | None,
):
    return body
