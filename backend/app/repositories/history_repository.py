from sqlalchemy.orm import Session

from app.models.history_event import HistoryEvent


def create_history_event(
    db: Session,
    event_type: str,
    property_id: int | None = None,
    content_id: int | None = None,
    faq_id: int | None = None,
    publishing_job_id: int | None = None,
    citation_test_run_id: int | None = None,
    source_type: str | None = None,
    actor: str = "system",
    status: str | None = None,
    summary: str | None = None,
    details: str | None = None,
    metadata_json: str | None = None,
):
    event = HistoryEvent(
        property_id=property_id,
        content_id=content_id,
        faq_id=faq_id,
        publishing_job_id=publishing_job_id,
        citation_test_run_id=citation_test_run_id,
        event_type=event_type,
        summary=summary,
        metadata_json=metadata_json or details,
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
    query = db.query(HistoryEvent)

    if property_id is not None:
        query = query.filter(HistoryEvent.property_id == property_id)

    return (
        query.order_by(HistoryEvent.created_at.desc())
        .limit(limit)
        .all()
    )
