from fastapi import (
    APIRouter,
    Depends
)

from datetime import datetime

from pydantic import BaseModel

from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.models.content import Content

from app.services.publishing_service import (
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


class PublishCompleteRequest(
    BaseModel
):
    content_id: int
    url: str
    dry_run: bool = False
    preview_title: str | None = None
    preview_subreddit: str | None = None
    preview_screenshot: str | None = None
    preview_timestamp: datetime | None = None


@router.post("/publish/{content_id}")
def publish_content_route(
    content_id: int,
    db: Session = Depends(get_db),
):

    result = publish_content(
        db=db,
        content_id=content_id
    )

    return result


@router.get("/pending")
def get_pending_publish(
    db: Session = Depends(get_db),
):

    content = (
        db.query(Content)
        .filter(
            Content.publish_status == "pending"
        )
        .first()
    )

    if not content:

        return {
            "task": None
        }

    return {
        "task": {
            "id": content.id,
            "title": extract_article_title(
                generated_content=content.body,
                fallback=content.title
            ),
            "body": content.body,
            "subreddit": "test"
        }
    }


@router.post("/complete")
def complete_publish(
    request: PublishCompleteRequest,
    db: Session = Depends(get_db),
):

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

    article_title = extract_article_title(
        generated_content=content.body,
        fallback=content.title
    )

    if request.dry_run:
        content.publish_status = "draft_prepared"
    else:
        content.publish_status = "published"

    if not request.dry_run:
        content.published_url = request.url

    content.publish_provider = "reddit"

    content.preview_title = request.preview_title
    content.preview_subreddit = request.preview_subreddit
    content.preview_screenshot = request.preview_screenshot
    content.preview_timestamp = request.preview_timestamp

    db.commit()

    if request.dry_run:
        event_type = "draft_prepared"
        event_summary = f"Draft Prepared for {article_title}"
    else:
        event_type = "published"
        event_summary = f"Published {article_title}"

    create_history_event(
        db=db,
        event_type=event_type,
        content_id=content.id,
        source_type=content.generation_mode,
        status=content.publish_status,
        summary=event_summary,
        details=request.preview_screenshot or request.url
    )

    return {
        "status": "success",
        "dry_run": request.dry_run,
        "publish_status": content.publish_status,
    }
