from sqlalchemy.orm import Session

from app.models.content_history import ContentHistoryEvent


def create_history_event(
    db: Session,
    event_type: str,
    content_id: int | None = None,
    source_type: str | None = None,
    actor: str = "system",
    status: str | None = None,
    summary: str | None = None,
    details: str | None = None,
):
    event = ContentHistoryEvent(
        content_id=content_id,
        event_type=event_type,
        source_type=source_type,
        actor=actor,
        status=status,
        summary=summary,
        details=details,
    )

    db.add(event)

    db.commit()

    db.refresh(event)

    return event


def get_recent_history_events(
    db: Session,
    limit: int = 100,
):
    return (
        db.query(ContentHistoryEvent)
        .order_by(ContentHistoryEvent.created_at.desc())
        .limit(limit)
        .all()
    )
