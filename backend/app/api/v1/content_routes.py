from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from fastapi.responses import HTMLResponse

from app.services.export_service import (
    generate_html_export
)

from app.models.content import Content

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

router = APIRouter(
    prefix="/api/v1/content",
    tags=["Content Engine"]
)


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
        target_url=request.target_url,
        mode=request.mode
    )

    return {
        "generated_content":
            result.body,

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
            "title": event.content.title if event.content else "System event",
            "body": event.content.body if event.content else event.details,
            "content_type": (
                event.content.content_type if event.content else None
            ),
            "target_persona": (
                event.content.target_persona if event.content else None
            ),
            "generation_mode": (
                event.content.generation_mode
                if event.content
                else event.source_type
            ),
            "publish_status": (
                event.content.publish_status if event.content else event.status
            ),
            "published_url": (
                event.content.published_url if event.content else None
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
                "title": content.title,
                "body": content.body,
                "content_type": content.content_type,
                "target_persona": content.target_persona,
                "generation_mode": content.generation_mode,
                "publish_status": content.publish_status,
                "published_url": content.published_url,
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
        "title": content.title,
        "body": content.body,
        "publish_status": content.publish_status,
        "published_url": content.published_url
    }
