from fastapi import (APIRouter, Depends)
from sqlalchemy.orm import Session

from app.services.citation_service import check_citation

from app.core.deps import get_db

router = APIRouter(
    prefix="/api/v1/citations",
    tags=["Citation Engine"]
)


@router.get("/check")
def citation_check(
    query: str,
    property_id: int | None = None,
    provider: str | None = "chatgpt",
    db: Session = Depends(get_db),
):

    result = check_citation(
        db=db,
        query=query,
        property_id=property_id,
        provider=provider,
    )

    return result
