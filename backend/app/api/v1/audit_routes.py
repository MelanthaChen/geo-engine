from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.services.property_service import get_property


router = APIRouter(
    prefix="/api/v1/audit",
    tags=["Website Audit"]
)


class AuditRunRequest(BaseModel):
    property_id: int


@router.post("/run")
def run_audit(
    request: AuditRunRequest,
    db: Session = Depends(get_db),
):
    property_record = get_property(db, request.property_id)

    if not property_record:
        raise HTTPException(status_code=404, detail="Property not found")

    return {
        "property_id": property_record.id,
        "property_name": property_record.name,
        "website_url": property_record.domain,
        "last_audit": datetime.now(timezone.utc).isoformat(),
        "overall_geo_score": None,
        "brand_understanding": {
            "status": "pending_analysis",
            "items": [
                "Audit crawler and brand understanding scoring are not connected yet."
            ],
        },
        "missing_pages": [],
        "missing_geo_topics": [],
        "internal_linking_suggestions": [],
        "faq_opportunities": [],
        "content_recommendations": [],
    }
