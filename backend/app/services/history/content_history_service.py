from app.models.content import Content


def serialize_generated_content(content: Content):
    return {
        "id": content.id,
        "property_id": content.property_id,
        "content_id": content.id,
        "source_faq_set_id": content.faq_set_id,
        "category": content.target_persona,
        "faq_source": content.faq_source,
        "content_type": content.content_type,
        "angle": content.angle,
        "perspective": content.perspective,
        "archetype": content.archetype,
        "internet_style": content.internet_style,
        "generated_angles": content.generated_angles,
        "title": content.title,
        "body": content.body,
        "website_url": content.target_url,
        "generation_timestamp": content.created_at,
        "created_at": content.created_at,
    }
