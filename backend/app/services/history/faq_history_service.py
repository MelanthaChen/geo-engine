from sqlalchemy.orm import Session

from app.models.faq import Faq
from app.models.faq_set import FaqSet
from app.core.llm_provider import normalize_llm_provider
from app.repositories.history_repository import create_history_event


def create_faq_set(
    db: Session,
    category: str,
    faq_source: str,
    questions: list[str],
    property_id: int | None = None,
    content_type: str | None = None,
    website_url: str | None = None,
    provider: str | None = None,
):
    faq_set = FaqSet(
        property_id=property_id,
        category=category,
        faq_source=faq_source,
        content_type=content_type,
        provider=normalize_llm_provider(provider),
        website_url=None,
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

    create_history_event(
        db=db,
        event_type="faq_generated",
        property_id=property_id,
        summary=f"{faq_source} FAQ generated for {category}",
        metadata_json="\n".join(questions),
    )

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
        "property_id": faq_set.property_id,
        "category": faq_set.category,
        "faq_source": faq_set.faq_source,
        "content_type": faq_set.content_type,
        "provider": faq_set.provider,
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
