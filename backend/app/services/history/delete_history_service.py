from sqlalchemy.orm import Session

from app.models.content_history import ContentHistoryEvent
from app.models.faq import Faq
from app.models.faq_set import FaqSet
from app.models.generated_content import GeneratedContent


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
    generated_content = (
        db.query(GeneratedContent)
        .filter(GeneratedContent.id == generated_content_id)
        .first()
    )

    if not generated_content:
        return False

    if generated_content.content_id:
        db.query(ContentHistoryEvent).filter(
            ContentHistoryEvent.content_id == generated_content.content_id
        ).delete(synchronize_session=False)

    db.delete(generated_content)
    db.commit()

    return True
