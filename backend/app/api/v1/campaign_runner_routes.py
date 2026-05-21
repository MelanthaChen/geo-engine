from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.services.campaign_runner_service import (
    run_campaign
)


router = APIRouter(
    prefix="/api/v1/campaigns",
    tags=["Campaign Runner"]
)


@router.post("/run/{campaign_id}")
def run_campaign_route(
    campaign_id: int,
    db: Session = Depends(get_db),
):

    result = run_campaign(
        campaign_id=campaign_id,
        db=db,
    )

    return result