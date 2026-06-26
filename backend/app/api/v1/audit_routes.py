from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.services.property_service import get_property
from app.services.website_audit.audit_service import (
    latest_website_audit,
    run_website_audit,
    serialize_audit,
)


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

    audit = run_website_audit(
        db=db,
        property_record=property_record,
    )

    return serialize_audit(
        audit=audit,
        property_record=property_record,
    )


@router.get("/latest")
def get_latest_audit(
    property_id: int = Query(...),
    db: Session = Depends(get_db),
):
    property_record = get_property(db, property_id)

    if not property_record:
        raise HTTPException(status_code=404, detail="Property not found")

    audit = latest_website_audit(
        db=db,
        property_id=property_id,
    )

    if not audit:
        return None

    return serialize_audit(
        audit=audit,
        property_record=property_record,
    )
