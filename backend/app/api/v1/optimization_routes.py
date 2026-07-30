from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.services.optimization_service import (
    optimize_content
)


router = APIRouter(
    prefix="/api/v1/optimization",
    tags=["Optimization Engine"]
)


@router.post("/optimize/{content_id}")
def optimize_content_route(
    content_id: int,
    provider: str | None = "chatgpt",
    db: Session = Depends(get_db),
):

    result = optimize_content(
        content_id=content_id,
        db=db,
        provider=provider,
    )

    return result
