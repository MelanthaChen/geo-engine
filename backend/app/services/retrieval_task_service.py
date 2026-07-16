from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.platform_question import PlatformQuestion
from app.models.retrieval_task import RetrievalTask
from app.services.faq_discovery.platform_faq_service import (
    save_platform_questions,
    serialize_platform_question,
)
from app.services.platform_retrievers import RetrievedPlatformQuestion


RETRIEVAL_TASK_STATUSES = {
    "queued",
    "processing",
    "completed",
    "failed",
}


def create_retrieval_task(
    db: Session,
    *,
    category: str,
    platform: str,
    content_type: str | None = None,
    property_id: int | None = None,
    account_id: int | None = None,
) -> RetrievalTask:
    task = RetrievalTask(
        property_id=property_id,
        account_id=account_id,
        platform=(platform or "").strip().lower(),
        category=category,
        content_type=content_type,
        status="queued",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def claim_next_retrieval_task(
    db: Session,
    *,
    platform: str = "xiaohongshu",
) -> RetrievalTask | None:
    task = (
        db.query(RetrievalTask)
        .filter(
            RetrievalTask.platform == platform,
            RetrievalTask.status == "queued",
        )
        .order_by(RetrievalTask.created_at.asc())
        .first()
    )

    if not task:
        return None

    task.status = "processing"
    db.commit()
    db.refresh(task)
    return task


def complete_retrieval_task(
    db: Session,
    *,
    task_id: int,
    questions: list[RetrievedPlatformQuestion],
) -> tuple[RetrievalTask | None, list[PlatformQuestion]]:
    task = db.query(RetrievalTask).filter(RetrievalTask.id == task_id).first()

    if not task:
        return None, []

    saved_questions = save_platform_questions(
        db=db,
        property_id=task.property_id,
        questions=questions,
    )

    task.status = "completed"
    task.result_count = len(saved_questions)
    task.error_message = None
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)

    return task, saved_questions


def fail_retrieval_task(
    db: Session,
    *,
    task_id: int,
    error_message: str,
) -> RetrievalTask | None:
    task = db.query(RetrievalTask).filter(RetrievalTask.id == task_id).first()

    if not task:
        return None

    task.status = "failed"
    task.error_message = error_message
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return task


def get_retrieval_task(
    db: Session,
    *,
    task_id: int,
) -> RetrievalTask | None:
    return db.query(RetrievalTask).filter(RetrievalTask.id == task_id).first()


def list_task_platform_questions(
    db: Session,
    *,
    task: RetrievalTask,
) -> list[dict]:
    if task.status != "completed":
        return []

    rows = (
        db.query(PlatformQuestion)
        .filter(
            PlatformQuestion.property_id == task.property_id,
            PlatformQuestion.platform == task.platform,
        )
        .order_by(PlatformQuestion.discovered_at.desc())
        .limit(task.result_count or 20)
        .all()
    )

    return [serialize_platform_question(row) for row in rows]


def serialize_retrieval_task(
    task: RetrievalTask,
    *,
    platform_questions: list[dict] | None = None,
) -> dict:
    return {
        "id": task.id,
        "property_id": task.property_id,
        "account_id": task.account_id,
        "platform": task.platform,
        "category": task.category,
        "content_type": task.content_type,
        "status": task.status,
        "result_count": task.result_count,
        "error_message": task.error_message,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "completed_at": task.completed_at,
        "platform_questions": platform_questions or [],
    }
