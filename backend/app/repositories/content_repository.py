from sqlalchemy.orm import Session

from app.models.content import Content


def create_content(
    db: Session,
    query_id: int,
    title: str,
    content_type: str,
    body: str,
    target_persona: str,
    property_id: int | None = None,
    generation_mode: str | None = None,
    strategy_type: str | None = None,
    target_url: str | None = None,
    evidence_json: str | None = None,
    ai_faq: str | None = None,
    platform_faq: str | None = None,
    faq_source: str | None = None,
    reddit_title: str | None = None,
    reddit_body: str | None = None,
    angle: str | None = None,
    perspective: str | None = None,
    archetype: str | None = None,
    internet_style: str | None = None,
    generated_angles: str | None = None,
):
    content = Content(
        property_id=property_id,
        query_id=query_id,
        title=title,
        content_type=content_type,
        strategy_type=strategy_type,
        generation_mode=generation_mode,
        target_url=target_url,
        evidence_json=evidence_json,
        ai_faq=ai_faq,
        platform_faq=platform_faq,
        faq_source=faq_source,
        angle=angle,
        perspective=perspective,
        archetype=archetype,
        internet_style=internet_style,
        generated_angles=generated_angles,
        body=body,
        reddit_title=reddit_title,
        reddit_body=reddit_body,
        target_persona=target_persona,
    )

    db.add(content)

    db.commit()

    db.refresh(content)

    return content

def get_all_contents(db: Session):

    return (
        db.query(Content)
        .order_by(Content.created_at.desc())
        .all()
    )

def get_all_contents_for_property(
    db: Session,
    property_id: int,
):
    return (
        db.query(Content)
        .filter(Content.property_id == property_id)
        .order_by(Content.created_at.desc())
        .all()
    )

def get_content_by_id(
    db,
    content_id: int,
):

    return (
        db.query(Content)
        .filter(Content.id == content_id)
        .first()
    )

def update_content_publish_info(
    db,
    content,
    publish_result,
):

    content.publish_status = "published"

    content.published_url = (
        publish_result["url"]
    )

    content.publish_provider = (
        publish_result["provider"]
    )

    db.commit()

    db.refresh(content)

    return content
