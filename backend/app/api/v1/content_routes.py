from fastapi import (
    APIRouter,
    Depends
)

import json

from sqlalchemy.orm import Session

from fastapi.responses import HTMLResponse

from app.services.export_service import (
    generate_html_export
)

from app.models.content import Content
from app.models.publish_task import PublishTask

from app.core.deps import get_db

from app.schemas.content_schema import (
    ContentGenerationRequest,
)

from app.services.content_service import (
    generate_content,
    fetch_all_contents,
    generate_faqs
)
from app.repositories.history_repository import (
    get_recent_history_events
)
from app.utils.title_extractor import (
    extract_article_title
)

router = APIRouter(
    prefix="/api/v1/content",
    tags=["Content Engine"]
)


def content_title(content: Content):
    if content.reddit_title:
        return content.reddit_title

    return extract_article_title(
        generated_content=content.body,
        fallback=content.title
    )


def content_evidence(content: Content):
    if not content.evidence_json:
        return None

    try:
        return json.loads(content.evidence_json)
    except Exception:
        return None


def latest_publish_task(
    db: Session,
    content_id: int,
):
    return (
        db.query(PublishTask)
        .filter(PublishTask.content_id == content_id)
        .order_by(PublishTask.created_at.desc())
        .first()
    )


def publish_metadata(
    db: Session,
    content: Content,
):
    task = latest_publish_task(
        db=db,
        content_id=content.id
    )

    return {
        "publish_task_id": task.id if task else None,
        "published_account": task.account.handle if task else None,
        "published_account_id": task.account_id if task else None,
        "published_platform": (
            task.account.platform
            if task
            else content.publish_provider
        ),
        "published_url": content.published_url,
    }


@router.post("/generate")
def generate_content_route(
    request: ContentGenerationRequest,
    db: Session = Depends(get_db),
):

    result = generate_content(
        db=db,
        query=request.query,
        persona=request.persona,
        content_type=request.content_type,
        target_url=request.product_url or request.target_url,
        mode=request.mode,
        ai_faq=request.ai_faq,
        platform_faq=request.platform_faq,
        faq_source=request.faq_source,
    )

    return {
        "generated_content":
            result.body,

        "title":
            result.title,

        "reddit_title":
            result.reddit_title,

        "reddit_body":
            result.reddit_body,

        "strategy_type":
            result.strategy_type,

        "content_type":
            result.content_type,

        "target_url":
            result.target_url,

        "evidence":
            content_evidence(result),

        "ai_faq":
            result.ai_faq,

        "platform_faq":
            result.platform_faq,

        "faq_source":
            result.faq_source,

        "content_id":
            result.id
    }


@router.get("/history")
def get_content_history(
    db: Session = Depends(get_db),
):

    contents = fetch_all_contents(db)

    events = get_recent_history_events(db)

    event_rows = [
        {
            "id": f"event-{event.id}",
            "event_id": event.id,
            "content_id": event.content_id,
            "title": (
                content_title(event.content)
                if event.content
                else "System event"
            ),
            "body": event.content.body if event.content else event.details,
            "reddit_title": (
                event.content.reddit_title if event.content else None
            ),
            "reddit_body": (
                event.content.reddit_body if event.content else None
            ),
            "content_type": (
                event.content.content_type if event.content else None
            ),
            "strategy_type": (
                event.content.strategy_type if event.content else None
            ),
            "target_persona": (
                event.content.target_persona if event.content else None
            ),
            "target_url": (
                event.content.target_url if event.content else None
            ),
            "evidence": (
                content_evidence(event.content) if event.content else None
            ),
            "ai_faq": (
                event.content.ai_faq if event.content else None
            ),
            "platform_faq": (
                event.content.platform_faq if event.content else None
            ),
            "faq_source": (
                event.content.faq_source if event.content else None
            ),
            "generation_mode": (
                event.content.generation_mode
                if event.content
                else event.source_type
            ),
            "publish_status": (
                event.content.publish_status if event.content else event.status
            ),
            **(
                publish_metadata(db, event.content)
                if event.content
                else {
                    "publish_task_id": None,
                    "published_account": None,
                    "published_account_id": None,
                    "published_platform": None,
                    "published_url": None,
                }
            ),
            "preview_title": (
                event.content.preview_title if event.content else None
            ),
            "preview_subreddit": (
                event.content.preview_subreddit if event.content else None
            ),
            "preview_screenshot": (
                event.content.preview_screenshot if event.content else None
            ),
            "preview_url": (
                event.content.preview_url if event.content else None
            ),
            "preview_timestamp": (
                event.content.preview_timestamp if event.content else None
            ),
            "citation_count": (
                event.content.citation_count if event.content else 0
            ),
            "visibility_score": (
                event.content.visibility_score if event.content else 0
            ),
            "event_type": event.event_type,
            "event_summary": event.summary,
            "event_status": event.status,
            "created_at": event.created_at,
        }
        for event in events
    ]

    if event_rows:
        return {
            "history": event_rows
        }

    return {
        "history": [
            {
                "id": content.id,
                "content_id": content.id,
                "title": content_title(content),
                "body": content.body,
                "reddit_title": content.reddit_title,
                "reddit_body": content.reddit_body,
                "content_type": content.content_type,
                "strategy_type": content.strategy_type,
                "target_persona": content.target_persona,
                "target_url": content.target_url,
                "evidence": content_evidence(content),
                "ai_faq": content.ai_faq,
                "platform_faq": content.platform_faq,
                "faq_source": content.faq_source,
                "generation_mode": content.generation_mode,
                "publish_status": content.publish_status,
                **publish_metadata(db, content),
                "preview_title": content.preview_title,
                "preview_subreddit": content.preview_subreddit,
                "preview_screenshot": content.preview_screenshot,
                "preview_url": content.preview_url,
                "preview_timestamp": content.preview_timestamp,
                "citation_count": content.citation_count,
                "visibility_score": content.visibility_score,
                "event_type": "legacy_content",
                "event_summary": "Legacy generated content",
                "event_status": content.publish_status,
                "created_at": content.created_at,
            }
            for content in contents
        ]
    }


@router.get("/faqs/{target}")
def generate_faqs_route(
    target: str,
    mode: str,
):

    faqs = generate_faqs(
        target,
        mode
    )

    print("FAQ RESULT:")
    print(faqs)

    return {
        "target": target,
        "mode": mode,
        "faqs": faqs
    }


@router.get(
    "/export/{content_id}",
    response_class=HTMLResponse
)
def export_content(
    content_id: int,
    db: Session = Depends(get_db),
):

    content = (
        db.query(Content)
        .filter(Content.id == content_id)
        .first()
    )

    if not content:

        return HTMLResponse(
            content="<h1>Content not found</h1>",
            status_code=404
        )

    html = generate_html_export(content)

    return HTMLResponse(content=html)

@router.get("/{content_id}")
def get_content_by_id(
    content_id: int,
    db: Session = Depends(get_db),
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

    return {
        "id": content.id,
        "title": content_title(content),
        "body": content.body,
        "reddit_title": content.reddit_title,
        "reddit_body": content.reddit_body,
        "content_type": content.content_type,
        "strategy_type": content.strategy_type,
        "target_url": content.target_url,
        "evidence": content_evidence(content),
        "ai_faq": content.ai_faq,
        "platform_faq": content.platform_faq,
        "faq_source": content.faq_source,
        "publish_status": content.publish_status,
        **publish_metadata(db, content),
        "preview_title": content.preview_title,
        "preview_subreddit": content.preview_subreddit,
        "preview_screenshot": content.preview_screenshot,
        "preview_url": content.preview_url,
        "preview_timestamp": content.preview_timestamp
    }
