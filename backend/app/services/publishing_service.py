from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.content import Content
from app.models.publish_task import PublishTask

from app.core.config import settings
from app.repositories.history_repository import (
    create_history_event
)
from app.utils.title_extractor import (
    extract_article_title
)


def publish_content(
    db: Session,
    content_id: int,
    account_id: int | None = None,
    publish_platform: str | None = None,
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

    account = select_publish_account(
        db=db,
        account_id=account_id,
        publish_platform=publish_platform,
    )

    if not account:
        return {
            "error": "No active publishing account found"
        }

    content.publish_status = "pending"

    article_title = (
        content.reddit_title
        or extract_article_title(
            generated_content=content.body,
            fallback=content.title
        )
    )

    publish_task = PublishTask(
        content_id=content.id,
        account_id=account.id,
        status="pending"
    )

    db.add(publish_task)

    db.commit()

    db.refresh(publish_task)

    create_history_event(
        db=db,
        event_type="publish_requested",
        content_id=content.id,
        source_type=content.generation_mode,
        status=content.publish_status,
        summary=(
            f"Publish requested for {article_title} "
            f"via {account.handle}"
        )
    )

    return {
        "status": "pending",
        "content_id": content.id,
        "publish_task_id": publish_task.id,
        "account_id": account.id,
        "account_handle": account.handle,
        "publish_platform": account.platform,
    }


def select_publish_account(
    db: Session,
    account_id: int | None = None,
    publish_platform: str | None = None,
):
    normalized_platform = (
        publish_platform or "reddit"
    ).strip().lower()

    if account_id:
        filters = [
            Account.id == account_id,
            Account.is_active.is_(True),
        ]

        if publish_platform:
            filters.append(Account.platform == normalized_platform)

        return db.query(Account).filter(*filters).first()

    active_accounts = (
        db.query(Account)
        .filter(
            Account.platform == normalized_platform,
            Account.is_active.is_(True)
        )
        .all()
    )

    if not active_accounts:
        return None

    return min(
        active_accounts,
        key=lambda account: (
            db.query(PublishTask)
            .filter(
                PublishTask.account_id == account.id,
                PublishTask.status.in_(["pending", "processing"])
            )
            .count()
        )
    )


def claim_pending_task(
    db: Session,
    account_id: int,
):
    task = (
        db.query(PublishTask)
        .filter(
            PublishTask.account_id == account_id,
            PublishTask.status == "pending"
        )
        .order_by(PublishTask.created_at.asc())
        .first()
    )

    if not task:
        return None

    task.status = "processing"
    task.content.publish_status = "processing"

    db.commit()
    db.refresh(task)

    return task


def mark_task_failed(
    db: Session,
    publish_task_id: int,
):
    task = (
        db.query(PublishTask)
        .filter(PublishTask.id == publish_task_id)
        .first()
    )

    if not task:
        return None

    task.status = "failed"
    task.content.publish_status = "failed"

    db.commit()
    db.refresh(task)

    create_history_event(
        db=db,
        event_type="publish_failed",
        content_id=task.content_id,
        source_type=task.content.generation_mode,
        status="failed",
        summary=(
            f"Publishing failed for {task.content.title} "
            f"via {task.account.handle}"
        )
    )

    return task
