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
    property_id: int | None = None,
    angle: str | None = None,
    perspective: str | None = None,
    archetype: str | None = None,
    internet_style: str | None = None,
    generated_angles: str | None = None,
):
    generated_content = GeneratedContent(
        property_id=property_id,
        category=category,
        faq_source=faq_source,
        content_type=content_type,
        angle=angle,
        perspective=perspective,
        archetype=archetype,
        internet_style=internet_style,
        generated_angles=generated_angles,
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
        "property_id": content.property_id,
        "content_id": content.content_id,
        "source_faq_set_id": content.source_faq_set_id,
        "category": content.category,
        "faq_source": content.faq_source,
        "content_type": content.content_type,
        "angle": content.angle,
        "perspective": content.perspective,
        "archetype": content.archetype,
        "internet_style": content.internet_style,
        "generated_angles": content.generated_angles,
        "title": content.title,
        "body": content.body,
        "website_url": content.website_url,
        "generation_timestamp": content.generation_timestamp,
        "created_at": content.created_at,
    }
