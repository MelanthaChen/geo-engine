from fastapi import (
    APIRouter,
    Depends
)

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

    content.publish_status = "published"

    content.published_url = request.url

    content.publish_provider = "reddit"

    article_title = extract_article_title(
        generated_content=content.body,
        fallback=content.title
    )

    db.commit()

    create_history_event(
        db=db,
        event_type="published",
        content_id=content.id,
        source_type=content.generation_mode,
        status=content.publish_status,
        summary=f"Published {article_title}",
        details=request.url
    )

    return {
        "status": "success"
    }
