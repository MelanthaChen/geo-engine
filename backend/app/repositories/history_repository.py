from sqlalchemy.orm import Session

from app.models.content_history import ContentHistoryEvent


def create_history_event(
    db: Session,
    event_type: str,
    property_id: int | None = None,
    content_id: int | None = None,
    source_type: str | None = None,
    actor: str = "system",
    status: str | None = None,
    summary: str | None = None,
    details: str | None = None,
):
    event = ContentHistoryEvent(
        property_id=property_id,
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
    property_id: int | None = None,
):
    query = db.query(ContentHistoryEvent)

    if property_id is not None:
        query = query.filter(ContentHistoryEvent.property_id == property_id)

    return (
        query.order_by(ContentHistoryEvent.created_at.desc())
        .limit(limit)
        .all()
    )
