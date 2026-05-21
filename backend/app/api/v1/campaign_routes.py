from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.models.campaign import Campaign


router = APIRouter(
    prefix="/api/v1/campaigns",
    tags=["Campaign Engine"]
)


@router.post("/create")
def create_campaign(
    name: str,
    target_brand: str,
    target_domain: str = "",
    competitors: str = "",
    target_keywords: str = "",
    target_queries: str = "",
    db: Session = Depends(get_db),
):

    campaign = Campaign(
        name=name,
        target_brand=target_brand,
        target_domain=target_domain,
        competitors=competitors,
        target_keywords=target_keywords,
        target_queries=target_queries,
    )

    db.add(campaign)

    db.commit()

    db.refresh(campaign)

    return campaign


@router.get("/")
def get_campaigns(
    db: Session = Depends(get_db),
):

    campaigns = (
        db.query(Campaign)
        .all()
    )

    return campaigns