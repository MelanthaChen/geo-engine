from fastapi import APIRouter

from app.schemas.query_schema import (
    QueryGenerationRequest,
    QueryGenerationResponse
)

from app.services.query_service import generate_queries


router = APIRouter()


@router.post(
    "/generate",
    response_model=QueryGenerationResponse
)
async def generate_query_list(
    request: QueryGenerationRequest
):

    queries = generate_queries(
        category=request.category,
        niche=request.niche
    )

    return {
        "queries": queries
    }