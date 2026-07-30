from fastapi import APIRouter
from fastapi import Depends

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.services.citation_test_service import (
    run_citation_test,
    run_prompt_citation_test,
)
from app.models.citation_test import CitationTest
from app.models.citation_test_run import CitationTestRun


router = APIRouter(
    prefix="/api/v1/citation-tests",
    tags=["Citation Testing Engine"]
)


class PromptCitationTestRequest(BaseModel):
    property_id: int
    prompt: str
    models: list[str]
    provider: str | None = "chatgpt"


@router.get("")
def list_tests(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):
    run_query = db.query(CitationTestRun)

    if property_id is not None:
        run_query = run_query.filter(CitationTestRun.property_id == property_id)

    runs = (
        run_query.order_by(CitationTestRun.created_at.desc())
        .limit(100)
        .all()
    )

    rows = []

    for run in runs:
        for result in run.results:
            rows.append(
                {
                    "id": result.id,
                    "run_id": run.id,
                    "property_id": run.property_id,
                    "content_id": None,
                    "platform": result.model,
                    "provider": result.provider,
                    "model": result.model,
                    "query": run.prompt,
                    "prompt": run.prompt,
                    "target_brand": run.target_brand,
                    "status": result.status or run.status,
                    "source_type": "prompt",
                    "citation_target": run.target_brand,
                    "ai_response": result.raw_response,
                    "raw_response": result.raw_response,
                    "response_snippet": result.response_snippet,
                    "mentioned": result.mentioned,
                    "rank": result.rank,
                    "evidence_found": result.mentioned,
                    "citation_type": (
                        "mention"
                        if result.mentioned
                        else "none"
                    ),
                    "confidence_score": None,
                    "visibility_score": None,
                    "matched_keywords": None,
                    "tested_at": result.tested_at or run.completed_at,
                    "last_run": result.tested_at or run.completed_at,
                    "created_at": run.created_at,
                }
            )

    legacy_query = db.query(CitationTest)

    if property_id is not None:
        legacy_query = legacy_query.filter(CitationTest.property_id == property_id)

    legacy_tests = (
        legacy_query.order_by(CitationTest.tested_at.desc())
        .limit(100)
        .all()
    )

    rows.extend(
        {
            "id": f"legacy-{test.id}",
            "run_id": None,
            "property_id": test.property_id,
            "content_id": test.content_id,
            "platform": test.platform,
            "provider": test.provider,
            "model": test.platform,
            "query": test.prompt or test.query,
            "prompt": test.prompt or test.query,
            "target_brand": test.target_brand,
            "status": test.status,
            "source_type": test.source_type,
            "citation_target": test.citation_target,
            "ai_response": test.ai_response,
            "raw_response": test.ai_response,
            "response_snippet": (
                test.ai_response[:320]
                if test.ai_response
                else None
            ),
            "mentioned": test.mentioned,
            "rank": None,
            "evidence_found": test.evidence_found,
            "citation_type": test.citation_type,
            "confidence_score": test.confidence_score,
            "visibility_score": test.visibility_score,
            "matched_keywords": test.matched_keywords,
            "tested_at": test.last_run or test.tested_at,
            "last_run": test.last_run or test.tested_at,
            "created_at": test.created_at,
        }
        for test in legacy_tests
    )

    return {
        "tests": sorted(
            rows,
            key=lambda row: row["last_run"] or row["created_at"],
            reverse=True,
        )
    }


@router.post("/run")
def run_prompt_test(
    request: PromptCitationTestRequest,
    db: Session = Depends(get_db),
):
    result = run_prompt_citation_test(
        db=db,
        property_id=request.property_id,
        prompt=request.prompt,
        models=request.models,
        provider=request.provider,
    )

    if not result:
        return {
            "error": "Property not found"
        }

    return {
        "run_id": result.id,
        "property_id": result.property_id,
        "prompt": result.prompt,
        "status": result.status,
        "results": [
            {
                "id": item.id,
                "model": item.model,
                "provider": item.provider,
                "status": item.status,
                "mentioned": item.mentioned,
                "rank": item.rank,
                "response_snippet": item.response_snippet,
                "raw_response": item.raw_response,
                "error_message": item.error_message,
                "tested_at": item.tested_at,
            }
            for item in result.results
        ],
    }


@router.post("/run/{content_id}")
def run_test(
    content_id: int,
    source_type: str = "published_content",
    property_id: int | None = None,
    provider: str | None = "chatgpt",
    db: Session = Depends(get_db),
):

    result = run_citation_test(
        db=db,
        content_id=content_id,
        source_type=source_type,
        property_id=property_id,
        provider=provider,
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
        "provider": result.provider,
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
