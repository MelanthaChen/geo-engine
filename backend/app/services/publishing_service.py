from sqlalchemy.orm import Session

from app.models.content import Content


def publish_content(
    db: Session,
    content_id: int,
):

    content = (
        db.query(Content)
        .filter(Content.id == content_id)
        .first()
    )

    if not content:

        return {
            "error": "Content not found"
        }

    content.publish_status = "pending"

    db.commit()

    return {
        "status": "pending",
        "content_id": content.id
    }