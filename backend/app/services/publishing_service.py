from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.content import Content
from app.models.publishing_job import PublishingJob

from app.core.config import settings
from app.repositories.history_repository import (
    create_history_event
)
from app.services.account_service import seed_demo_accounts
from app.utils.title_extractor import (
    extract_article_title
)


def append_job_log(
    job: PublishingJob,
    message: str,
):
    existing_logs = job.logs or ""
    job.logs = f"{existing_logs}{message}\n"


def publish_content(
    db: Session,
    content_id: int,
    account_id: int | None = None,
    publish_platform: str | None = None,
    property_id: int | None = None,
):

    query = db.query(Content).filter(Content.id == content_id)

    if property_id is not None:
        query = query.filter(Content.property_id == property_id)

    content = query.first()

    if not content:

        return {
            "error": "Content not found"
        }

    account = select_publish_account(
        db=db,
        account_id=account_id,
        publish_platform=publish_platform,
        property_id=content.property_id,
    )

    if not account and content.property_id is not None:
        seed_demo_accounts(db, property_id=content.property_id)
        account = select_publish_account(
            db=db,
            account_id=account_id,
            publish_platform=publish_platform,
            property_id=content.property_id,
        )

    if not account:
        return {
            "error": "No active publishing account found"
        }

    content.publish_status = "queued"
    content.publish_platform = account.platform

    article_title = (
        content.reddit_title
        or extract_article_title(
            generated_content=content.body,
            fallback=content.title
        )
    )

    publishing_job = PublishingJob(
        property_id=content.property_id,
        content_id=content.id,
        account_id=account.id,
        platform=account.platform,
        status="queued",
    )
    append_job_log(publishing_job, "Publishing job queued.")

    db.add(publishing_job)

    db.commit()

    db.refresh(publishing_job)

    create_history_event(
        db=db,
        event_type="publish_requested",
        property_id=content.property_id,
        content_id=content.id,
        publishing_job_id=publishing_job.id,
        source_type=content.generation_mode,
        status=content.publish_status,
        summary=(
            f"Publish requested for {article_title} "
            f"via {account.handle}"
        )
    )

    return {
        "status": "queued",
        "content_id": content.id,
        "publish_job_id": publishing_job.id,
        "publish_task_id": publishing_job.id,
        "account_id": account.id,
        "account_handle": account.handle,
        "publish_platform": account.platform,
    }


def select_publish_account(
    db: Session,
    account_id: int | None = None,
    publish_platform: str | None = None,
    property_id: int | None = None,
):
    normalized_platform = (
        publish_platform or "reddit"
    ).strip().lower()

    if account_id:
        filters = [
            Account.id == account_id,
            Account.is_active.is_(True),
        ]

        if property_id is not None:
            filters.append(Account.property_id == property_id)

        if publish_platform:
            filters.append(Account.platform == normalized_platform)

        return db.query(Account).filter(*filters).first()

    filters = [
        Account.platform == normalized_platform,
        Account.is_active.is_(True),
    ]

    if property_id is not None:
        filters.append(Account.property_id == property_id)

    active_accounts = db.query(Account).filter(*filters).all()

    if not active_accounts:
        return None

    return min(
        active_accounts,
        key=lambda account: (
            count_active_tasks(
                db=db,
                account_id=account.id,
                property_id=property_id,
            )
        )
    )


def count_active_tasks(
    db: Session,
    account_id: int,
    property_id: int | None = None,
):
    filters = [
        PublishingJob.account_id == account_id,
        PublishingJob.status.in_(["queued", "processing"]),
    ]

    if property_id is not None:
        filters.append(PublishingJob.property_id == property_id)

    return db.query(PublishingJob).filter(*filters).count()


def claim_pending_task(
    db: Session,
    account_id: int,
    property_id: int | None = None,
):
    filters = [
        PublishingJob.account_id == account_id,
        PublishingJob.status == "queued",
    ]

    if property_id is not None:
        filters.append(PublishingJob.property_id == property_id)

    job = (
        db.query(PublishingJob)
        .filter(*filters)
        .order_by(PublishingJob.created_at.asc())
        .first()
    )

    if not job:
        return None

    job.status = "processing"
    append_job_log(job, "Worker claimed job. Status changed to processing.")
    job.content.publish_status = "processing"

    db.commit()
    db.refresh(job)

    create_history_event(
        db=db,
        event_type="publish_processing",
        property_id=job.property_id,
        content_id=job.content_id,
        publishing_job_id=job.id,
        status="processing",
        summary=f"Publishing job processing via {job.account.handle}",
        details=job.logs,
    )

    return job


def mark_task_failed(
    db: Session,
    publish_task_id: int,
):
    task = (
        db.query(PublishingJob)
        .filter(PublishingJob.id == publish_task_id)
        .first()
    )

    if not task:
        return None

    task.status = "failed"
    append_job_log(task, "Publishing job failed.")
    task.content.publish_status = "failed"

    db.commit()
    db.refresh(task)

    create_history_event(
        db=db,
        event_type="publish_failed",
        property_id=task.property_id,
        content_id=task.content_id,
        publishing_job_id=task.id,
        source_type=task.content.generation_mode,
        status="failed",
        summary=(
            f"Publishing failed for {task.content.title} "
            f"via {task.account.handle}"
        ),
        details=task.logs,
    )

    return task
