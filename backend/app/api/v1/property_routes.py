from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.citation_test import CitationTest
from app.models.citation_test_run import CitationTestRun
from app.models.content import Content
from app.models.publishing_job import PublishingJob
from app.services.property_service import (
    create_property,
    get_property,
    list_properties,
    update_property,
)


router = APIRouter(
    prefix="/api/v1/properties",
    tags=["Properties"]
)


class PropertyCreateRequest(BaseModel):
    name: str
    domain: str
    brand_name: str | None = None
    description: str | None = None


class PropertyUpdateRequest(BaseModel):
    name: str | None = None
    domain: str | None = None
    brand_name: str | None = None
    description: str | None = None


def serialize_property(property_record):
    return {
        "id": property_record.id,
        "name": property_record.name,
        "domain": property_record.domain,
        "brand_name": property_record.brand_name,
        "description": property_record.description,
        "created_at": property_record.created_at,
        "updated_at": property_record.updated_at,
    }


@router.get("")
def get_properties(
    db: Session = Depends(get_db),
):
    return [
        serialize_property(property_record)
        for property_record in list_properties(db)
    ]


@router.post("")
def post_property(
    request: PropertyCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        return serialize_property(
            create_property(
                db=db,
                name=request.name,
                domain=request.domain,
                brand_name=request.brand_name or request.name,
                description=request.description,
            )
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A property with this domain already exists"
        )


@router.get("/{property_id}")
def get_property_route(
    property_id: int,
    db: Session = Depends(get_db),
):
    property_record = get_property(db, property_id)

    if not property_record:
        raise HTTPException(status_code=404, detail="Property not found")

    return serialize_property(property_record)


@router.patch("/{property_id}")
def patch_property(
    property_id: int,
    request: PropertyUpdateRequest,
    db: Session = Depends(get_db),
):
    try:
        property_record = update_property(
            db=db,
            property_id=property_id,
            name=request.name,
            domain=request.domain,
            brand_name=request.brand_name,
            description=request.description,
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A property with this domain already exists"
        )

    if not property_record:
        raise HTTPException(status_code=404, detail="Property not found")

    return serialize_property(property_record)


@router.get("/{property_id}/metrics")
def get_property_metrics(
    property_id: int,
    db: Session = Depends(get_db),
):
    property_record = get_property(db, property_id)

    if not property_record:
        raise HTTPException(status_code=404, detail="Property not found")

    generated_content_count = (
        db.query(Content)
        .filter(Content.property_id == property_id)
        .count()
    )

    published_content_count = (
        db.query(Content)
        .filter(
            Content.property_id == property_id,
            Content.publish_status == "published",
        )
        .count()
    )

    pending_publish_count = (
        db.query(PublishingJob)
        .filter(
            PublishingJob.property_id == property_id,
            PublishingJob.status.in_(["queued", "processing", "review_ready"]),
        )
        .count()
    )

    citation_count = (
        db.query(CitationTestRun)
        .filter(
            CitationTestRun.property_id == property_id,
            CitationTestRun.status == "finished",
        )
        .count()
    )

    latest_visibility = (
        db.query(CitationTest)
        .filter(CitationTest.property_id == property_id)
        .order_by(CitationTest.tested_at.desc())
        .first()
    )

    visibility_score = (
        latest_visibility.visibility_score
        if latest_visibility
        else 0
    )

    return {
        "property_id": property_id,
        "generated_content": generated_content_count,
        "published_content": published_content_count,
        "tracked_prompts": pending_publish_count,
        "citation_count": citation_count,
        "visibility_score": visibility_score,
        "clicks": 0,
        "impressions": 0,
    }
