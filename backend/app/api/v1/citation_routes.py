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
    db: Session = Depends(get_db),
):

    result = check_citation(
        db=db,
        query=query
    )

    return result