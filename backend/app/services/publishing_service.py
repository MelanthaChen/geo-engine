from sqlalchemy.orm import Session

from app.models.content import Content

from app.core.config import settings
from app.repositories.history_repository import (
    create_history_event
)


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

    create_history_event(
        db=db,
        event_type="publish_requested",
        content_id=content.id,
        source_type=content.generation_mode,
        status=content.publish_status,
        summary=f"Publish requested for {content.title}"
    )

    return {
        "status": "pending",
        "content_id": content.id
    }
