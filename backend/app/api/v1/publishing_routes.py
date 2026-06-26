from fastapi import (
    APIRouter,
    Depends
)

from datetime import datetime

from pydantic import BaseModel

from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.models.content import Content
from app.models.publishing_job import PublishingJob

from app.services.publishing_service import (
    append_job_log,
    claim_pending_task,
    mark_task_failed,
    publish_content
)
from app.repositories.history_repository import (
    create_history_event
)
from app.utils.title_extractor import (
    extract_article_title
)

router = APIRouter(
    prefix="/api/v1/publishing",
    tags=["Publishing Engine"]
)

PUBLISH_TASK_STATUSES = {
    "queued",
    "processing",
    "review_ready",
    "published",
    "failed",
}


def content_title(content: Content):
    if content.reddit_title:
        return content.reddit_title

    return extract_article_title(
        generated_content=content.body,
        fallback=content.title
    )


class PublishCompleteRequest(
    BaseModel
):
    content_id: int
    url: str
    publish_task_id: int | None = None
    status: str = "review_ready"
    preview_title: str | None = None
    preview_subreddit: str | None = None
    preview_url: str | None = None
    preview_screenshot: str | None = None
    preview_timestamp: datetime | None = None


class PublishFailedRequest(
    BaseModel
):
    publish_task_id: int


@router.post("/publish/{content_id}")
def publish_content_route(
    content_id: int,
    account_id: int | None = None,
    publish_platform: str | None = None,
    property_id: int | None = None,
    db: Session = Depends(get_db),
):

    result = publish_content(
        db=db,
        content_id=content_id,
        account_id=account_id,
        publish_platform=publish_platform,
        property_id=property_id,
    )

    return result


@router.get("/pending")
def get_pending_publish(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    filters = [PublishingJob.status == "queued"]

    if property_id is not None:
        filters.append(PublishingJob.property_id == property_id)

    task = (
        db.query(PublishingJob)
        .filter(*filters)
        .order_by(PublishingJob.created_at.asc())
        .first()
    )

    if not task:
        return {
            "task": None
        }

    return get_pending_publish_for_account(
        account_id=task.account_id,
        property_id=property_id,
        db=db
    )


@router.get("/tasks")
def get_publish_tasks(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(PublishingJob)

    if property_id is not None:
        query = query.filter(PublishingJob.property_id == property_id)

    tasks = (
        query.order_by(PublishingJob.created_at.desc())
        .limit(100)
        .all()
    )

    return {
        "tasks": [
            {
                "id": task.id,
                "property_id": task.property_id,
                "content_id": task.content_id,
                "title": content_title(task.content),
                "platform": task.platform,
                "account_handle": (
                    task.account.handle if task.account else None
                ),
                "status": task.status,
                "logs": task.logs,
                "error_message": task.error_message,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
            for task in tasks
        ]
    }


@router.get("/pending/{account_id}")
def get_pending_publish_for_account(
    account_id: int,
    agent_name: str | None = None,
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    task = claim_pending_task(
        db=db,
        account_id=account_id,
        property_id=property_id,
    )

    if not task:

        return {
            "task": None
        }

    if agent_name:
        task.account.agent_name = agent_name
        db.commit()

    content = task.content

    adapted_title, adapted_body = adapt_content_for_platform(
        content=content,
        publish_platform=task.account.platform,
    )

    return {
        "task": {
            "id": task.id,
            "publish_task_id": task.id,
            "content_id": content.id,
            "property_id": task.property_id,
            "account_id": task.account_id,
            "account_handle": task.account.handle,
            "platform": task.account.platform,
            "title": adapted_title,
            "body": adapted_body,
            "target_url": content.target_url,
            "subreddit": "test"
        }
    }


@router.post("/failed")
def fail_publish_task(
    request: PublishFailedRequest,
    db: Session = Depends(get_db),
):
    task = mark_task_failed(
        db=db,
        publish_task_id=request.publish_task_id
    )

    if not task:
        return {
            "error": "Publish task not found"
        }

    return {
        "status": "failed",
        "publish_task_id": task.id
    }


@router.post("/complete")
def complete_publish(
    request: PublishCompleteRequest,
    db: Session = Depends(get_db),
):
    if request.status not in PUBLISH_TASK_STATUSES:
        return {
            "error": "Invalid publish task status"
        }

    publish_task = None

    if request.publish_task_id:
        publish_task = (
            db.query(PublishingJob)
            .filter(PublishingJob.id == request.publish_task_id)
            .first()
        )

    content = (
        db.query(Content)
        .filter(
            Content.id == request.content_id
        )
        .first()
    )

    if not content:

        return {
            "error": "Content not found"
        }

    if publish_task:
        publish_task.status = request.status
        append_job_log(
            publish_task,
            f"Worker reported status {request.status}.",
        )

    article_title = extract_article_title(
        generated_content=content.body,
        fallback=content.title
    )

    content.publish_status = request.status

    if request.status == "published":
        content.published_url = request.url
        content.publish_url = request.url

    content.publish_provider = (
        publish_task.account.platform
        if publish_task
        else None
    )
    content.publish_platform = content.publish_provider

    content.preview_title = request.preview_title
    content.preview_subreddit = request.preview_subreddit
    content.preview_url = request.preview_url or request.url
    content.preview_screenshot = request.preview_screenshot
    content.preview_timestamp = request.preview_timestamp

    db.commit()

    if request.status == "review_ready":
        event_type = "review_ready"
        event_summary = f"Review Ready for {article_title}"
    elif request.status == "published":
        event_type = "published"
        event_summary = f"Published {article_title}"
    else:
        event_type = request.status
        event_summary = f"{request.status} for {article_title}"

    if publish_task:
        event_summary = (
            f"{event_summary} via {publish_task.account.handle}"
        )

    create_history_event(
        db=db,
        event_type=event_type,
        property_id=content.property_id,
        content_id=content.id,
        publishing_job_id=publish_task.id if publish_task else None,
        source_type=content.generation_mode,
        status=content.publish_status,
        summary=event_summary,
        details=(
            publish_task.logs
            if publish_task
            else request.preview_screenshot or request.url
        )
    )

    return {
        "status": "success",
        "publish_task_id": publish_task.id if publish_task else None,
        "account_id": publish_task.account_id if publish_task else None,
        "publish_status": content.publish_status,
    }


def adapt_content_for_platform(
    content: Content,
    publish_platform: str,
):
    normalized_platform = (publish_platform or "").strip().lower()

    title = (
        content.reddit_title
        or extract_article_title(
            generated_content=content.body,
            fallback=content.title
        )
    )

    if normalized_platform != "reddit":
        return title, content.body

    if content.reddit_body:
        return title, content.reddit_body

    return title, build_reddit_discussion_body(content)


def build_reddit_discussion_body(content: Content):
    body = (content.body or "").strip()

    lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip()
    ]

    cleaned_lines = [
        line
        for line in lines
        if not line.lower().startswith(
            (
                "title:",
                "summary:",
                "full article:",
                "faq:",
                "references:",
            )
        )
    ]

    excerpt = "\n\n".join(cleaned_lines[:6]).strip()

    if len(excerpt) > 1800:
        excerpt = excerpt[:1800].rsplit(" ", 1)[0].strip()

    question = (
        "Curious how other people are thinking about this. "
        "What tradeoffs or details would you pay attention to?"
    )

    if not excerpt:
        excerpt = (
            "I have been looking into this topic and trying to separate "
            "useful information from generic advice."
        )

    return f"{excerpt}\n\n{question}"
