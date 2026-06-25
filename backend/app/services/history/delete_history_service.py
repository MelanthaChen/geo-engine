from sqlalchemy.orm import Session

from app.models.history_event import HistoryEvent
from app.models.faq import Faq
from app.models.faq_set import FaqSet
from app.models.content import Content


def delete_faq_set(
    db: Session,
    faq_set_id: int,
):
    faq_set = (
        db.query(FaqSet)
        .filter(FaqSet.id == faq_set_id)
        .first()
    )

    if not faq_set:
        return False

    db.query(Faq).filter(
        Faq.faq_set_id == faq_set.id
    ).delete(synchronize_session=False)

    db.delete(faq_set)
    db.commit()

    return True


def delete_generated_content(
    db: Session,
    generated_content_id: int,
):
    content = (
        db.query(Content)
        .filter(Content.id == generated_content_id)
        .first()
    )

    if not content:
        return False

    db.query(HistoryEvent).filter(
        HistoryEvent.content_id == content.id
    ).delete(synchronize_session=False)

    db.delete(content)
    db.commit()

    return True
