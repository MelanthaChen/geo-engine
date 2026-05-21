from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.schemas.content_schema import (
    ContentGenerationRequest,
)

from app.services.content_service import generate_content

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
    content_type=request.content_type
)

    return {
        "generated_content": result
    }