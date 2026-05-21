from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.services.citation_test_service import (
    run_citation_test
)


router = APIRouter(
    prefix="/api/v1/citation-tests",
    tags=["Citation Testing Engine"]
)


@router.post("/run/{content_id}")
def run_test(
    content_id: int,
    db: Session = Depends(get_db),
):

    result = run_citation_test(
        db=db,
        content_id=content_id
    )

    if not result:

        return {
            "error": "Content not found"
        }

    return {
        "test_id": result.id,
        "content_id": result.content_id,
        "platform": result.platform,
        "mentioned": result.mentioned,
        "visibility_score":
            result.visibility_score,
        "matched_keywords":
            result.matched_keywords,
    }