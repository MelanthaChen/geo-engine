from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.services.citation_test_service import (
    run_citation_test
)
from app.models.citation_test import CitationTest


router = APIRouter(
    prefix="/api/v1/citation-tests",
    tags=["Citation Testing Engine"]
)


@router.get("")
def list_tests(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(CitationTest)

    if property_id is not None:
        query = query.filter(CitationTest.property_id == property_id)

    tests = (
        query.order_by(CitationTest.tested_at.desc())
        .limit(100)
        .all()
    )

    return {
        "tests": [
            {
                "id": test.id,
                "property_id": test.property_id,
                "content_id": test.content_id,
                "platform": test.platform,
                "query": test.query,
                "source_type": test.source_type,
                "citation_target": test.citation_target,
                "ai_response": test.ai_response,
                "mentioned": test.mentioned,
                "evidence_found": test.evidence_found,
                "citation_type": test.citation_type,
                "confidence_score": test.confidence_score,
                "visibility_score": test.visibility_score,
                "matched_keywords": test.matched_keywords,
                "tested_at": test.tested_at,
            }
            for test in tests
        ]
    }


@router.post("/run/{content_id}")
def run_test(
    content_id: int,
    source_type: str = "published_content",
    property_id: int | None = None,
    db: Session = Depends(get_db),
):

    result = run_citation_test(
        db=db,
        content_id=content_id,
        source_type=source_type,
        property_id=property_id,
    )

    if not result:

        return {
            "error": "Content not found"
        }

    return {
        "test_id": result.id,
        "content_id": result.content_id,
        "property_id": result.property_id,
        "platform": result.platform,
        "mentioned": result.mentioned,
        "evidence_found": result.evidence_found,
        "citation_type": result.citation_type,
        "confidence_score": result.confidence_score,
        "visibility_score":
            result.visibility_score,
        "matched_keywords":
            result.matched_keywords,
        "ai_response": result.ai_response,
    }
