from sqlalchemy.orm import Session

from app.models.faq import Faq
from app.models.faq_set import FaqSet


def create_faq_set(
    db: Session,
    category: str,
    faq_source: str,
    questions: list[str],
    content_type: str | None = None,
    website_url: str | None = None,
):
    faq_set = FaqSet(
        category=category,
        faq_source=faq_source,
        content_type=content_type,
        website_url=website_url,
    )

    db.add(faq_set)
    db.flush()

    for rank, question in enumerate(questions, start=1):
        db.add(
            Faq(
                faq_set_id=faq_set.id,
                question=question,
                rank=rank,
            )
        )

    db.commit()
    db.refresh(faq_set)

    return faq_set


def get_faq_set(
    db: Session,
    faq_set_id: int,
):
    return (
        db.query(FaqSet)
        .filter(FaqSet.id == faq_set_id)
        .first()
    )


def get_latest_faq_set(
    db: Session,
    category: str,
    faq_source: str,
):
    return (
        db.query(FaqSet)
        .filter(
            FaqSet.category == category,
            FaqSet.faq_source == faq_source,
        )
        .order_by(FaqSet.created_at.desc())
        .first()
    )


def serialize_faq_set(faq_set: FaqSet | None):
    if not faq_set:
        return None

    return {
        "id": faq_set.id,
        "category": faq_set.category,
        "faq_source": faq_set.faq_source,
        "content_type": faq_set.content_type,
        "website_url": faq_set.website_url,
        "created_at": faq_set.created_at,
        "questions": [
            faq.question
            for faq in sorted(faq_set.faqs, key=lambda item: item.rank)
        ],
        "faqs": [
            {
                "id": faq.id,
                "question": faq.question,
                "rank": faq.rank,
                "created_at": faq.created_at,
            }
            for faq in sorted(faq_set.faqs, key=lambda item: item.rank)
        ],
    }
