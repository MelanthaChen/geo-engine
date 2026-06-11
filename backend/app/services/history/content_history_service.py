from sqlalchemy.orm import Session

from app.models.generated_content import GeneratedContent


def create_generated_content(
    db: Session,
    category: str,
    faq_source: str,
    content_type: str,
    title: str,
    body: str,
    website_url: str | None,
    source_faq_set_id: int | None,
    content_id: int | None,
):
    generated_content = GeneratedContent(
        category=category,
        faq_source=faq_source,
        content_type=content_type,
        title=title,
        body=body,
        website_url=website_url,
        source_faq_set_id=source_faq_set_id,
        content_id=content_id,
    )

    db.add(generated_content)
    db.commit()
    db.refresh(generated_content)

    return generated_content


def serialize_generated_content(content: GeneratedContent):
    return {
        "id": content.id,
        "content_id": content.content_id,
        "source_faq_set_id": content.source_faq_set_id,
        "category": content.category,
        "faq_source": content.faq_source,
        "content_type": content.content_type,
        "title": content.title,
        "body": content.body,
        "website_url": content.website_url,
        "created_at": content.created_at,
    }
