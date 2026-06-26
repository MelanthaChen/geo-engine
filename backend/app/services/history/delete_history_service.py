from sqlalchemy.orm import Session

from app.models.history_event import HistoryEvent
from app.models.faq import Faq
from app.models.faq_set import FaqSet
from app.models.content import Content
from app.models.publishing_job import PublishingJob
from app.models.publish_task import PublishTask
from app.models.citation_test import CitationTest
from app.models.citation_result import CitationResult
from app.models.citation_test_run import CitationTestRun
from app.models.citation_test_result import CitationTestResult


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
    db.query(PublishingJob).filter(
        PublishingJob.content_id == content.id
    ).delete(synchronize_session=False)
    db.query(PublishTask).filter(
        PublishTask.content_id == content.id
    ).delete(synchronize_session=False)

    legacy_tests = (
        db.query(CitationTest)
        .filter(CitationTest.content_id == content.id)
        .all()
    )

    for citation_test in legacy_tests:
        db.query(CitationResult).filter(
            CitationResult.citation_test_id == citation_test.id
        ).delete(synchronize_session=False)
        db.delete(citation_test)

    db.delete(content)
    db.commit()

    return True


def delete_publishing_job(
    db: Session,
    publishing_job_id: int,
):
    job = (
        db.query(PublishingJob)
        .filter(PublishingJob.id == publishing_job_id)
        .first()
    )

    if not job:
        return False

    db.query(HistoryEvent).filter(
        HistoryEvent.publishing_job_id == job.id
    ).delete(synchronize_session=False)

    db.delete(job)
    db.commit()

    return True


def delete_citation_test_run(
    db: Session,
    citation_test_run_id: int,
):
    citation_run = (
        db.query(CitationTestRun)
        .filter(CitationTestRun.id == citation_test_run_id)
        .first()
    )

    if not citation_run:
        return False

    db.query(HistoryEvent).filter(
        HistoryEvent.citation_test_run_id == citation_run.id
    ).delete(synchronize_session=False)
    db.query(CitationTestResult).filter(
        CitationTestResult.run_id == citation_run.id
    ).delete(synchronize_session=False)

    db.delete(citation_run)
    db.commit()

    return True


def delete_history_event(
    db: Session,
    history_event_id: int,
):
    event = (
        db.query(HistoryEvent)
        .filter(HistoryEvent.id == history_event_id)
        .first()
    )

    if not event:
        return False

    db.delete(event)
    db.commit()

    return True


def delete_history_item(
    db: Session,
    item_type: str,
    item_id: int,
):
    normalized_type = item_type.strip().lower()

    if normalized_type == "faq":
        return delete_faq_set(db=db, faq_set_id=item_id)

    if normalized_type in {"generated_content", "content"}:
        return delete_generated_content(db=db, generated_content_id=item_id)

    if normalized_type in {"publish", "publishing_job"}:
        return delete_publishing_job(db=db, publishing_job_id=item_id)

    if normalized_type in {"citation_test", "citation"}:
        return delete_citation_test_run(
            db=db,
            citation_test_run_id=item_id,
        )

    if normalized_type in {"event", "audit"}:
        return delete_history_event(db=db, history_event_id=item_id)

    return False
