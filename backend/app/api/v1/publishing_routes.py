from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.services.publishing_service import (
    publish_content
)

router = APIRouter(
    prefix="/api/v1/publishing",
    tags=["Publishing Engine"]
)


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