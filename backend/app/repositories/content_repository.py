from sqlalchemy.orm import Session

from app.models.content import Content


def create_content(
    db: Session,
    query_id: int,
    title: str,
    content_type: str,
    body: str,
    target_persona: str,
):
    content = Content(
        query_id=query_id,
        title=title,
        content_type=content_type,
        body=body,
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