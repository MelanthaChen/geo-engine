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
        ontent_type=request.content_type,
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

    return contents


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